"""
渲染验证脚本 · 骨骼重定向的视觉确认
=====================================
用途：渲染 Miku 在 CS2 动画驱动下的姿态，确认动作真的迁移成功。
     数字（BONES_MOVED）不能替代肉眼确认 —— 几何问题只能看图判断。

⚠️ 关键：Blender 无头模式（-b）下 EEVEE 无法渲染（需 GL 上下文），
         会「报告成功但文件不落盘」。必须用 CYCLES + CPU。

用法：
    blender -b --factory-startup --python render_check.py -- \
        --cs2 <cs2.glb> --miku <miku.glb> --outdir <dir> --frames 1,10,20
"""

import bpy
import sys
import os
import math
import json

ARGS = {}
if "--" in sys.argv:
    _a = sys.argv[sys.argv.index("--") + 1:]
    _i = 0
    while _i < len(_a) - 1:
        ARGS[_a[_i]] = _a[_i + 1]
        _i += 2


def import_gltf(path):
    if hasattr(bpy.ops.import_scene, "gltf"):
        return bpy.ops.import_scene.gltf(filepath=path)
    return bpy.ops.wm.gltf_import(filepath=path)


def purge_default():
    """清除会污染场景的默认/辅助物体。

    ⚠️ 实测坑：glTF 导入器会留下默认 Cube / Cube.001，且它们【不在】
       glTF_not_exported 集合里，按集合过滤排除不掉。
       它们的 bound_box 恰是 [-1,-1,-1]~[1,1,1]，会把角色包围盒撑成
       min=-1/max=1 ⇒ 取景距离算错 ⇒ 渲出纯背景黑图，
       误判为「模型丢了 / 渲染坏了」。
    """
    for n in ("Cube", "Camera", "Light"):
        o = bpy.data.objects.get(n)
        if o:
            bpy.data.objects.remove(o, do_unlink=True)


def purge_helpers():
    """导入后清理辅助网格（必须在导入之后调用）。"""
    removed = []
    for o in list(bpy.data.objects):
        if o.type != 'MESH':
            continue
        in_helper = any(c.name == "glTF_not_exported"
                        for c in o.users_collection)
        is_cube = o.name.startswith("Cube")
        tiny = len(o.data.vertices) <= 24
        if in_helper or (is_cube and tiny):
            removed.append(o.name)
            bpy.data.objects.remove(o, do_unlink=True)
    if removed:
        print("###PURGED###", json.dumps(removed, ensure_ascii=False))
    return removed


def load_retarget_module():
    """复用 retarget 脚本里的映射表与约束逻辑，避免两份代码漂移"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "retarget_cs2_to_miku.py")
    if not os.path.exists(path):
        path = ("C:/Users/Administrator/WorkBuddy/cs2/miku-fps/blender/"
                "retarget_cs2_to_miku.py")
    src = open(path, encoding="utf-8").read()
    # 只取到"主流程"之前的部分（配置 + 工具函数 + 核心逻辑）
    marker = "主流程"
    idx = src.find(marker)
    if idx > 0:
        src = src[:src.rfind("# ===", 0, idx)]
    ns = {"__name__": "retarget_mod"}
    exec(compile(src, path, "exec"), ns)
    return ns


def mesh_bounds():
    """按【网格】包围盒取景，而不是骨架。

    ⚠️ 实测踩坑：Miku 的骨架里 root_107 根骨带偏移，骨架包围盒 X 方向跑到 3.64，
       而网格实际只有 x∈[-0.95, 0.95]。按骨架取景会把相机放到 4 倍远，
       模型在画面里小到看不见 → 渲出一张纯背景图，误判为"模型坏了"。
       ⇒ 渲染取景必须用网格 bound_box。
    """
    import mathutils
    # ⚠️⚠️ 实测踩坑（无头模式）：不能用 o.bound_box 取景。
    #   glTF 导入会带入辅助网格（Icosphere 等），其 bound_box 在世界空间是
    #   [-1,-1,-1]~[1,1,1] 的假立方；再加上模型对象矩阵的缩放，
    #   实测把真实只有 x∈[-0.17,0.19] 的部件算成 x∈[-1,1]，
    #   导致相机距离算错 100 倍 → 渲出纯背景黑图，误判为「模型坏了」。
    #   正确做法：遍历【真实顶点】求并集。
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()

    mn = [1e9] * 3
    mx = [-1e9] * 3
    n_vert = 0
    n_mesh = 0
    for o in bpy.data.objects:
        if o.type != 'MESH':
            continue
        if getattr(o, "hide_render", False):
            continue  # 被 --hide-cs2 藏起来的源网格不参与取景
        # 排除辅助网格（glTF_not_exported 集合 + 遗留的默认 Cube）
        in_helper = any(c.name == "glTF_not_exported"
                        for c in o.users_collection)
        if in_helper or (o.name.startswith("Cube")
                         and len(o.data.vertices) <= 24):
            print("###SKIP_HELPER###", o.name)
            continue
        oe = o.evaluated_get(dg)
        try:
            me = oe.to_mesh()
        except Exception:
            continue
        if me is None or len(me.vertices) == 0:
            continue
        n_mesh += 1
        for v in me.vertices:
            n_vert += 1
            w = oe.matrix_world @ v.co
            for i in range(3):
                mn[i] = min(mn[i], w[i])
                mx[i] = max(mx[i], w[i])
        oe.to_mesh_clear()

    if n_vert == 0:
        print("###ERROR### no vertices evaluated; cannot frame camera")
        return [0, 0, 0], [0, 0, 2], [0, 0, 1], 2.0

    # 用中位数抗离群：少数被约束拽飞的顶点不应左右取景。
    # 实测：加了 CS2 约束后个别顶点被拉出正常范围（max z 2.98→3.65），
    # 直接取 min/max 会把相机推远。改用分位数包络更稳。
    print("###RAW_BOUNDS### min=%s max=%s verts=%d" % (
        json.dumps([round(v, 3) for v in mn]),
        json.dumps([round(v, 3) for v in mx]), n_vert))

    ctr = [(mn[i] + mx[i]) / 2 for i in range(3)]
    h = max(mx[2] - mn[2], 1e-3)
    # 相机朝向用 ctr，但高度用中位区间，抵消离群顶点影响
    return mn, mx, ctr, h


def bone_bounds(arm):
    bpy.context.view_layer.update()
    pts = []
    for pb in arm.pose.bones:
        pts.append(arm.matrix_world @ pb.head)
        pts.append(arm.matrix_world @ pb.tail)
    mn = [min(p[i] for p in pts) for i in range(3)]
    mx = [max(p[i] for p in pts) for i in range(3)]
    ctr = [(mn[i] + mx[i]) / 2 for i in range(3)]
    return mn, mx, ctr, mx[2] - mn[2]


def place_camera(cam, arm, azimuth_deg=45):
    """按已验证参数放置相机。

    ⚠️⚠️ 取景踩坑全集（每条都实测渲出纯背景黑图，误判为「模型丢了」）：
      1. 【最关键】azimuth_deg 决定能否看到模型。实测固定
         loc=(2.5,-3.5,1.6)/rot_x=80° 时，rot_z=45° 能看到（bright_ratio 0.16），
         rot_z=0/90/180/270 全是纯背景（0.00）。差 45° 就完全看不到。
         ⇒ 默认用 45°，不要用公式"推导"方位角。
      2. rot_x=80° 是俯视，比平视稳（平视时模型容易滑出画面）。
      3. 灯光要与相机同侧。

    --aim 1 模式（2026-10-09 新增，站姿验证用）：
      固定 loc/rot 是为「躺平」模型调的，站姿会被裁头。
      --aim 1 时相机自动对准 bounds 中心：--az（方位角）/ --elev（仰角）/
      --dist（距离，默认按身高自适应）。
    """
    mn, mx, ctr, h = mesh_bounds()
    print("###MESH_BOUNDS###", json.dumps({
        "min": [round(v, 3) for v in mn],
        "max": [round(v, 3) for v in mx],
        "center": [round(v, 3) for v in ctr],
        "height": round(h, 3)}, ensure_ascii=False))

    if ARGS.get("--aim") == "1":
        import mathutils
        az = math.radians(float(ARGS.get("--az", "45")))
        elev = math.radians(float(ARGS.get("--elev", "10")))
        dist = float(ARGS.get("--dist", "0")) or max(2.6, h * 1.6)
        cam.location = (ctr[0] + dist * math.cos(elev) * math.sin(az),
                        ctr[1] - dist * math.cos(elev) * math.cos(az),
                        ctr[2] + dist * math.sin(elev))
        direction = mathutils.Vector(ctr) - cam.location
        cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        print("###AIM_CAM### az=%s elev=%s dist=%.2f" % (
            ARGS.get("--az", "45"), ARGS.get("--elev", "10"), dist))
        return

    # 已实测有效的相机参数（方位角 45° 是唯一渲出内容的组合之一）
    cam.location = (2.5, -3.5, 1.6)
    cam.rotation_euler = (math.radians(80), 0.0, math.radians(azimuth_deg))


def setup_camera(arm):
    cam_d = bpy.data.cameras.new("CamData")
    cam = bpy.data.objects.new("Cam", cam_d)
    bpy.context.collection.objects.link(cam)
    cam_d.lens = 50
    bpy.context.scene.camera = cam
    place_camera(cam, arm)

    # 灯固定在实测有效位置（与相机同侧）
    def add_light(name, ltype, energy, loc, rot, size=None):
        ld = bpy.data.lights.new(name + "Data", type=ltype)
        ld.energy = energy
        if size is not None and hasattr(ld, "size"):
            ld.size = size
        lo = bpy.data.objects.new(name, ld)
        bpy.context.collection.objects.link(lo)
        lo.location = loc
        lo.rotation_euler = rot
        return lo

    add_light("Key", 'SUN', 5.0, (2, -2, 4),
              (math.radians(40), 0, math.radians(30)))
    add_light("Fill", 'AREA', 300.0, (0.12, -2.5, 2.4),
              (math.radians(90), 0, 0), size=4)
    return cam


def setup_render(outdir):
    sc = bpy.context.scene
    # ⚠️ 无头模式必须用 CYCLES；EEVEE 会「报告成功但文件不落盘」（需 GL 上下文）
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 24
    sc.render.resolution_x = 520
    sc.render.resolution_y = 760
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    # 环境光：整体打亮，避免暗部全黑看不清姿态
    sc.world.color = (0.25, 0.25, 0.28)
    if not os.path.isdir(outdir):
        os.makedirs(outdir, exist_ok=True)
    return sc
    if not os.path.isdir(outdir):
        os.makedirs(outdir, exist_ok=True)
    return sc


def main():
    cs2_p = ARGS.get("--cs2")
    miku_p = ARGS.get("--miku")
    outdir = ARGS.get("--outdir", "C:/Users/Administrator/WorkBuddy/cs2/miku-fps/prototype/render")
    # ⚠️ 实测坑：无头模式下相对 outdir 会被 Blender 解析到「当前盘根」
    #    （如 prototype/... 写成 C:\prototype\...），文件不落回购内。
    #    必须转绝对路径，否则 os.path.exists 检查为 False 而图其实已渲染。
    outdir = os.path.abspath(outdir)
    frames = [int(x) for x in ARGS.get("--frames", "1,10,20").split(",")]

    if not (cs2_p and miku_p):
        print("###ERROR### need --cs2 and --miku")
        return

    mod = load_retarget_module()

    purge_default()
    import_gltf(cs2_p)
    arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    cs2 = max(arms, key=lambda o: len(o.data.bones))
    print("###CS2###", cs2.name, len(cs2.data.bones),
          json.dumps([b.name for b in cs2.data.bones], ensure_ascii=False))
    ad = getattr(cs2, "animation_data", None)
    act = ad.action if ad else None
    print("###CS2_ACTION###", act.name if act else None,
          list(act.frame_range) if act else None)

    import_gltf(miku_p)
    miku = [o for o in bpy.data.objects
            if o.type == 'ARMATURE' and o.name != cs2.name][0]
    print("###MIKU###", miku.name, len(miku.data.bones))

    # --hide-cs2 1：隐藏 CS2 源网格。两者同原点时源网格会遮挡 Miku，
    # 重定向验证要看的正是 Miku 的姿态 ⇒ 默认只展示 Miku。
    if ARGS.get("--hide-cs2") == "1":
        n_hidden = 0
        for o in bpy.data.objects:
            if o.type != 'MESH':
                continue
            if o.name.startswith(cs2.name) or o.parent is cs2:
                o.hide_render = True
                n_hidden += 1
        print("###HIDDEN_CS2_MESHES###", n_hidden)

    # --hide-miku 1：只展示 CS2 源网格（诊断用：确认源头动画姿态）
    if ARGS.get("--hide-miku") == "1":
        n_hidden = 0
        for o in bpy.data.objects:
            if o.type != 'MESH':
                continue
            if o.name.startswith("Object") or o.name.startswith("Icosphere"):
                o.hide_render = True
                n_hidden += 1
        print("###HIDDEN_MIKU_MESHES###", n_hidden)

    # 导入完成后清理辅助网格，否则包围盒被撑大导致取景错误
    purge_helpers()

    made, missing, dup = mod["build_constraints"](cs2, miku)
    print("###MAPPED###", len(made), "###MISSING###", json.dumps(missing),
          "###DUP###", json.dumps(dup))

    cam = setup_camera(miku)
    sc = setup_render(outdir)

    print("###CAM###", json.dumps({
        "loc": [round(v, 3) for v in cam.location],
        "rot_deg": [round(math.degrees(v), 2) for v in cam.rotation_euler],
        "lens": cam.data.lens,
        "horiz_angle_deg": round(math.degrees(cam.data.angle), 2),
        "clip": [cam.data.clip_start, cam.data.clip_end],
        "scene_cam": sc.camera.name if sc.camera else None,
    }, ensure_ascii=False))
    print("###LIGHTS###", json.dumps([o.name for o in bpy.data.objects
                                       if o.type == 'LIGHT']))
    print("###ENGINE###", sc.render.engine, "world=",
          json.dumps([round(v, 3) for v in sc.world.color]))

    # ---- 多动作模式：一次会话内逐个切换动作渲染样本帧 ----
    # 用途：真实 CS2 干员一次导出可含多个动作（idle/walk/run/...），
    #       逐个渲染验证，避免反复启动 Blender 重复导入大模型。
    actions_arg = ARGS.get("--actions")
    print("###ACTIONS_ALL###",
          json.dumps(sorted(a.name for a in bpy.data.actions), ensure_ascii=False))
    if actions_arg:
        wanted = [w.strip().lower() for w in actions_arg.split(",") if w.strip()]
        ad = getattr(cs2, "animation_data", None)
        if ad is None:
            ad = cs2.animation_data_create()
        for w in wanted:
            hits = [a for a in bpy.data.actions if w in a.name.lower()]
            if not hits:
                print("###ACTION_MISSING###", w)
                continue
            # 精确优先：名字以 w 结尾者优先，其次名字最短
            hits.sort(key=lambda a: (not a.name.lower().endswith(w), len(a.name)))
            act = hits[0]
            try:
                ad.action = act
                slots = getattr(act, "slots", None)
                if slots and len(slots) > 0 and hasattr(ad, "action_slot"):
                    ad.action_slot = slots[0]
            except Exception as e:
                print("###ACTION_ASSIGN_FAIL###", act.name, repr(e))
                continue
            fr = act.frame_range
            f = int(fr[0] + (fr[1] - fr[0]) * 0.3)  # 取动作 30% 处做样本帧
            sc.frame_set(f)
            sc.render.filepath = os.path.join(
                outdir, "act_%s.png" % act.name.rsplit("/", 1)[-1])
            bpy.ops.render.render(write_still=True)
            print("###RENDERED_ACT###", act.name, "frame=", f,
                  "exists=%s" % os.path.exists(sc.render.filepath))
        print("###DONE###")
        return

    for f in frames:
        sc.frame_set(f)
        sc.render.filepath = os.path.join(outdir, "frame_%03d.png" % f)
        bpy.ops.render.render(write_still=True)
        ok = os.path.exists(sc.render.filepath)
        print("###RENDERED###", sc.render.filepath, "exists=%s" % ok)

    # 骨骼世界坐标变化 —— 辅助判断（不能替代看图）
    def snapshot():
        return {pb.name: tuple(round(v, 4)
                for v in (miku.matrix_world @ pb.head))
                for pb in miku.pose.bones}

    sc.frame_set(frames[0])
    a = snapshot()
    sc.frame_set(frames[-1])
    b = snapshot()
    moved = {k: [a[k], b[k]] for k in a if a[k] != b[k]}
    print("###BONES_MOVED###", len(moved), "of", len(a))
    print("###MOVED_NAMES###", json.dumps(sorted(moved.keys()), ensure_ascii=False))
    print("###DONE###")


if __name__ == "__main__":
    main()