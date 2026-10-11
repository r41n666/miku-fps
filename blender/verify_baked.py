"""出厂产物复检：重新导入 miku_anim6.glb（最终交付 glb）并渲染指定动作两个时刻
================================================================
用途：对「已经烘焙+导出的最终 glb」做独立回环验证（走 glTF 导入器，
      与烘焙会话无关），用渲染图确认动作在成品里真正生效。

用法：
    blender -b --factory-startup --python verify_baked.py -- \
        --glb <miku_anim6.glb> --outdir <dir> [--action walk] [--az 45] [--elev 5] [--dist 3.6]
"""
import bpy
import sys
import os
import math

ARGS = {}
if "--" in sys.argv:
    a = sys.argv[sys.argv.index("--") + 1:]
    i = 0
    while i < len(a) - 1:
        ARGS[a[i]] = a[i + 1]
        i += 2

for n in ("Cube", "Camera", "Light"):
    o = bpy.data.objects.get(n)
    if o:
        bpy.data.objects.remove(o, do_unlink=True)

p = ARGS["--glb"]
if hasattr(bpy.ops.import_scene, "gltf"):
    bpy.ops.import_scene.gltf(filepath=p)
else:
    bpy.ops.wm.gltf_import(filepath=p)

arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
arm = max(arms, key=lambda o: len(o.data.bones))
print("###ARMATURE###", arm.name, len(arm.data.bones))

sub = ARGS.get("--action", "walk").lower()
hits = [a for a in bpy.data.actions if sub in a.name.lower()]
if not hits:
    print("###ACTION_MISSING###", sub, "have:",
          [a.name for a in bpy.data.actions])
    sys.exit(1)
hits.sort(key=lambda a: (not a.name.lower().endswith(sub), len(a.name)))
act = hits[0]
ad = arm.animation_data or arm.animation_data_create()
ad.action = act
try:
    slots = getattr(act, "slots", None)
    if slots and len(slots) > 0 and hasattr(ad, "action_slot"):
        ad.action_slot = slots[0]
except Exception:
    pass
fr = act.frame_range
f1 = int(fr[0] + (fr[1] - fr[0]) * 0.3)
f2 = int(fr[0] + (fr[1] - fr[0]) * 0.75)
print("###ACTION###", act.name, "range", tuple(fr), "frames", f1, f2)

# 相机对准可见网格
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
dg.update()
mn = [1e9] * 3
mx = [-1e9] * 3
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    if any(c.name == "glTF_not_exported" for c in o.users_collection):
        continue
    oe = o.evaluated_get(dg)
    me = oe.to_mesh()
    if me is None or len(me.vertices) == 0:
        continue
    for v in me.vertices:
        w = oe.matrix_world @ v.co
        for k in range(3):
            mn[k] = min(mn[k], w[k])
            mx[k] = max(mx[k], w[k])
    oe.to_mesh_clear()
ctr = [(mn[k] + mx[k]) / 2 for k in range(3)]
h = max(mx[2] - mn[2], 1e-3)
print("###BOUNDS### min=%s max=%s h=%.3f" % (
    [round(v, 3) for v in mn], [round(v, 3) for v in mx], h))

cam_d = bpy.data.cameras.new("C")
cam = bpy.data.objects.new("C", cam_d)
bpy.context.collection.objects.link(cam)
bpy.context.scene.camera = cam
cam_d.lens = 50
import mathutils
az = math.radians(float(ARGS.get("--az", "45")))
elev = math.radians(float(ARGS.get("--elev", "5")))
dist = float(ARGS.get("--dist", "0")) or max(2.6, h * 1.6)
cam.location = (ctr[0] + dist * math.cos(elev) * math.sin(az),
                ctr[1] - dist * math.cos(elev) * math.cos(az),
                ctr[2] + dist * math.sin(elev))
dvec = mathutils.Vector(ctr) - cam.location
cam.rotation_euler = dvec.to_track_quat('-Z', 'Y').to_euler()

ld = bpy.data.lights.new("K", type='SUN')
ld.energy = 5.0
lo = bpy.data.objects.new("K", ld)
bpy.context.collection.objects.link(lo)
lo.location = (2, -2, 4)
lo.rotation_euler = (math.radians(40), 0, math.radians(30))

sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 24
sc.render.resolution_x = 520
sc.render.resolution_y = 760
sc.world.color = (0.25, 0.25, 0.28)

outdir = os.path.abspath(ARGS["--outdir"])
os.makedirs(outdir, exist_ok=True)
for f in (f1, f2):
    sc.frame_set(f)
    sc.render.filepath = os.path.join(outdir, "baked_f%03d.png" % f)
    bpy.ops.render.render(write_still=True)
    print("###RENDERED###", sc.render.filepath,
          os.path.exists(sc.render.filepath))
print("###DONE###")
