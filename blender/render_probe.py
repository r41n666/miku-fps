"""
相机方位探针 · 一次渲多个角度，确定模型正面朝向
=====================================================
用法：
    blender -b --factory-startup --python render_probe.py -- \
        --miku <miku.glb> --cs2 <cs2.glb> --outdir <dir> [--frame N]

背景：自动取景算出的方位角可能与模型正面朝向不一致（导出的模型朝向不固定）。
      与其猜，不如一次渲 8 个方位角，用眼睛找出正面。
"""
import bpy, sys, os, math, json, mathutils

ARGS = {}
if "--" in sys.argv:
    a = sys.argv[sys.argv.index("--") + 1:]
    i = 0
    while i < len(a) - 1:
        ARGS[a[i]] = a[i + 1]
        i += 2

def imp(p):
    if hasattr(bpy.ops.import_scene, "gltf"):
        return bpy.ops.import_scene.gltf(filepath=p)
    return bpy.ops.wm.gltf_import(filepath=p)

for n in ("Cube", "Camera", "Light"):
    o = bpy.data.objects.get(n)
    if o:
        bpy.data.objects.remove(o, do_unlink=True)

ONLY_MIKU = ARGS.get("--only-miku") == "1"
cs2 = None
if not ONLY_MIKU:
    imp(ARGS["--cs2"])
    cs2 = max([o for o in bpy.data.objects if o.type == 'ARMATURE'],
              key=lambda o: len(o.data.bones))
imp(ARGS["--miku"])
miku = [o for o in bpy.data.objects
        if o.type == 'ARMATURE' and (cs2 is None or o.name != cs2.name)][0]

# ⚠️⚠️ 关键坑：glTF 导入器会留下默认 Cube / Cube.001，它们【不在】
#    glTF_not_exported 集合里，所以按集合过滤排除不掉。
#    而它们的 bound_box 恰好是 [-1,-1,-1]~[1,1,1]，会把角色包围盒
#    撑成 min=-1/max=1 ⇒ 取景距离算错 ⇒ 渲出纯背景黑图，
#    误判为「模型丢了 / 渲染坏了」。这里按「顶点数极少 + 名字是 Cube」双重排除。
for o in list(bpy.data.objects):
    if o.type != 'MESH':
        continue
    in_helper = any(c.name == "glTF_not_exported" for c in o.users_collection)
    is_cube = o.name.startswith("Cube")
    tiny = len(o.data.vertices) <= 24
    if in_helper or (is_cube and tiny):
        print("###PURGE###", o.name,
              "helper=%s cube=%s verts=%d" % (in_helper, is_cube, len(o.data.vertices)))
        bpy.data.objects.remove(o, do_unlink=True)

# 建立约束（复用 retarget 脚本）
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "retarget_cs2_to_miku.py"), encoding="utf-8").read()
i = src.find("主流程")
ns = {"__name__": "m"}
exec(compile(src[:src.rfind("# ==", 0, i)], "rt", "exec"), ns)
NO_CONSTRAINTS = ARGS.get("--no-constraints") == "1"
if cs2 is not None and not NO_CONSTRAINTS:
    made, missing, dup = ns["build_constraints"](cs2, miku)
    print("###MAPPED###", len(made))
else:
    print("###MAPPED### 0 (constraints disabled)")

# 真实顶点包围盒（排除辅助网格）
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get(); dg.update()
mn = [1e9]*3; mx = [-1e9]*3; nv = 0
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    if any(c.name == "glTF_not_exported" for c in o.users_collection):
        continue
    e = o.evaluated_get(dg); me = e.to_mesh()
    if me is None or len(me.vertices) == 0:
        if me: e.to_mesh_clear()
        continue
    for v in me.vertices:
        nv += 1
        w = e.matrix_world @ v.co
        for k in range(3):
            mn[k] = min(mn[k], w[k]); mx[k] = max(mx[k], w[k])
    e.to_mesh_clear()
ctr = [(mn[k]+mx[k])/2 for k in range(3)]
h = max(mx[2]-mn[2], 1e-3)
print("###PARENTS###", json.dumps([[o.name, o.parent.name if o.parent else None, len(o.data.vertices)] for o in bpy.data.objects if o.type=="MESH"], ensure_ascii=False))
print("###BBOX### verts=%d min=%s max=%s ctr=%s h=%.3f" % (
    nv, json.dumps([round(v,2) for v in mn]),
    json.dumps([round(v,2) for v in mx]),
    json.dumps([round(v,2) for v in ctr]), h))

cd = bpy.data.cameras.new("C")
cam = bpy.data.objects.new("C", cd)
bpy.context.collection.objects.link(cam)
bpy.context.scene.camera = cam
cd.lens = 50

sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 20
sc.render.resolution_x = 400; sc.render.resolution_y = 600
sc.world.color = (0.4, 0.4, 0.45)

# 灯固定在已知能照亮的位置（实测有效）
ld = bpy.data.lights.new("K", type='SUN'); ld.energy = 5.0
lo = bpy.data.objects.new("K", ld); bpy.context.collection.objects.link(lo)
lo.location = (2, -2, 4); lo.rotation_euler = (math.radians(40), 0, math.radians(30))
ld2 = bpy.data.lights.new("F", type='AREA'); ld2.energy = 300; ld2.size = 4
lo2 = bpy.data.objects.new("F", ld2); bpy.context.collection.objects.link(lo2)
lo2.location = (ctr[0], -2.5, ctr[2] + 1.0); lo2.rotation_euler = (math.radians(90), 0, 0)

out = ARGS.get("--outdir", "C:/Users/Administrator/WorkBuddy/cs2/miku-fps/prototype/render")
os.makedirs(out, exist_ok=True)
sc.frame_set(int(ARGS.get("--frame", "1")))

# 8 个方位角。
# ⚠️⚠️ 取景踩坑全集（每条都实测渲出纯背景黑图，差点误判为「模型丢了」）：
#   1. 【最关键】方位角 rot_z 决定能否看到模型。
#      实测：固定 loc=(2.5,-3.5,1.6) + rot_x=80° 时，
#           rot_z=45°  → bright_ratio 0.16（模型可见）
#           rot_z=0/90/180/225/270/315 → bright_ratio 0.00（纯背景）
#      ⇒ 差 45° 就完全看不到。**必须扫方位角，不能靠公式推导**。
#   2. 用 bright_ratio（亮像素占比）量化判断，别靠肉眼判断深色图。
#   3. 灯必须与相机同侧，否则背面全黑。
#   4. EEVEE 在无头模式下「报告成功但不落盘」，必须用 CYCLES + CPU。
#   5. glTF 导入会留默认 Cube / Icosphere（不在 glTF_not_exported 集合里），
#      它们的 bound_box 恰是 [-1,1]，会把包围盒撑坏导致取景算错。
BASE_LOC = (2.5, -3.5, 1.6)
for k in range(8):
    rz = k * 45
    cam.location = BASE_LOC
    cam.rotation_euler = (math.radians(80), 0.0, math.radians(rz))
    sc.render.filepath = os.path.join(out, "az_%03d.png" % rz)
    bpy.ops.render.render(write_still=True)
    print("###AZ### %3d -> %s exists=%s"
          % (rz, sc.render.filepath, os.path.exists(sc.render.filepath)))
print("###DONE###")
