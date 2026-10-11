"""
烘焙重定向动画 · CS2 干员动画 → Miku 骨骼（烘焙成独立 Action）
================================================================
用途：把「约束驱动」的实时重定向结果逐帧烘焙成 Miku 自己的动作，
      然后导出 FBX / glTF 供 Godot 使用（Godot 不认识 Blender 约束）。

用法：
    blender -b --factory-startup --python bake_retarget.py -- \
        --cs2 <cs2.glb> --miku <miku.glb> \
        --actions "idle_rifle,walk_n_rifle" \
        --out-fbx <out.fbx> [--out-glb <out.glb>] [--fps 30]

原理（「视觉键烘焙」）：
    1. 复用 retarget 脚本建立 RT_ 约束（含骨架转正 + 双命名自动选表）
    2. 每个动作逐帧读取 Miku 骨骼【约束求值后】的 pose matrix，
       反解出 basis（局部旋转）写入新 Action —— 只烘焙被约束的骨（21 根）
    3. 全部烘完移除 RT_ 约束（否则实时约束会覆盖烘焙结果 ⇒ 双重变形）
    4. 自检：约束态矩阵 vs 烘焙回放矩阵的最大误差角（应 ≈ 0°）

⚠️ 实测要点：
    · pose bone.matrix 在 view_layer.update() 后即为约束求值结果（armature 空间）
    · 先读全帧矩阵、再写 keys（写值会触碰 pose 状态）
    · 无骨盆位移（当前只做旋转）
"""
import bpy
import sys
import os
import json
import math

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


def load_retarget_module():
    """复用 retarget 脚本的映射表 / 约束 / 转正逻辑，避免两份实现漂移"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "retarget_cs2_to_miku.py")
    src = open(path, encoding="utf-8").read()
    idx = src.find("主流程")
    if idx > 0:
        src = src[:src.rfind("# ==", 0, idx)]
    ns = {"__name__": "rt"}
    exec(compile(src, path, "exec"), ns)
    return ns


def find_action(sub):
    hits = [a for a in bpy.data.actions if sub.lower() in a.name.lower()]
    if not hits:
        return None
    hits.sort(key=lambda a: (not a.name.lower().endswith(sub.lower()),
                             len(a.name)))
    return hits[0]


def assign_action(obj, act):
    ad = getattr(obj, "animation_data", None)
    if ad is None:
        ad = obj.animation_data_create()
    ad.action = act
    try:
        slots = getattr(act, "slots", None)
        if slots and len(slots) > 0 and hasattr(ad, "action_slot"):
            ad.action_slot = slots[0]
    except Exception:
        pass
    return ad


def basis_of(pb, mats):
    """由【约束求值后的矩阵】反解 pose bone 的 basis（局部旋转）。

    M_pose = M_parent_pose · M_parent_rest⁻¹ · M_rest · M_basis
    """
    parent = pb.parent
    if parent is not None:
        ref = (mats[parent.name]
               @ parent.bone.matrix_local.inverted()
               @ pb.bone.matrix_local)
    else:
        ref = pb.bone.matrix_local.copy()
    return ref.inverted() @ mats[pb.name]


def main():
    cs2_p = ARGS.get("--cs2")
    miku_p = ARGS.get("--miku")
    actions_arg = ARGS.get("--actions", "idle_rifle,walk_n_rifle")
    out_fbx = ARGS.get("--out-fbx")
    out_glb = ARGS.get("--out-glb")
    fps = int(ARGS.get("--fps", "30"))

    if not (cs2_p and miku_p):
        print("###ERROR### need --cs2 and --miku")
        return

    sc = bpy.context.scene
    sc.render.fps = fps
    sc.render.fps_base = 1.0

    mod = load_retarget_module()

    # 清默认物体
    for n in ("Cube", "Camera", "Light"):
        o = bpy.data.objects.get(n)
        if o:
            bpy.data.objects.remove(o, do_unlink=True)

    import_gltf(cs2_p)
    arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    cs2 = max(arms, key=lambda o: len(o.data.bones))
    import_gltf(miku_p)
    miku = [o for o in bpy.data.objects
            if o.type == 'ARMATURE' and o.name != cs2.name][0]

    # 清理 glTF 辅助网格
    for o in list(bpy.data.objects):
        if o.type != 'MESH':
            continue
        in_helper = any(c.name == "glTF_not_exported" for c in o.users_collection)
        if in_helper or (o.name.startswith("Cube") and len(o.data.vertices) <= 24):
            bpy.data.objects.remove(o, do_unlink=True)

    if miku.animation_data is None:
        miku.animation_data_create()

    # 建立约束（含骨架转正）
    made, missing, dup = mod["build_constraints"](cs2, miku)
    print("###MAPPED###", len(made), "###MISSING###", json.dumps(missing))

    # 被约束的 Miku 骨 = 要烘焙的骨（名字保持稳定顺序）
    baked_bones = [pb.name for pb in miku.pose.bones
                   if any(c.name.startswith("RT_") for c in pb.constraints)]
    print("###BAKE_BONES###", len(baked_bones))

    subset = [w.strip() for w in actions_arg.split(",") if w.strip()]
    baked = []
    check_expected = {}   # (act_name, frame) -> {bone: matrix}

    for w in subset:
        act = find_action(w)
        if act is None:
            print("###BAKE_ACTION_MISSING###", w)
            continue
        assign_action(cs2, act)
        fr = act.frame_range
        f0, f1 = int(fr[0]), int(max(fr[1], fr[0]))
        short = act.name.rsplit("/", 1)[-1]
        new_act = bpy.data.actions.new("MKI_" + short)
        new_act.use_fake_user = True
        assign_action(miku, new_act)

        # 自检采样帧：首帧 / 30% / 末帧
        sample_frames = {f0, f0 + int((f1 - f0) * 0.3), f1}
        n_keys = 0
        for f in range(f0, f1 + 1):
            sc.frame_set(f)
            bpy.context.view_layer.update()
            # ① 先读全帧矩阵（约束求值后）。注意采集【全部】pose bones：
            #    被烘焙骨的父骨可能是未映射骨（如 hips_106 的父 root_107），
            #    basis 反解需要父骨矩阵。
            mats = {pb.name: pb.matrix.copy() for pb in miku.pose.bones}
            if f in sample_frames:
                check_expected[(new_act.name, f)] = {
                    n: mats[n] for n in baked_bones}
            # ② 再写 basis 并打 key
            for name in baked_bones:
                pb = miku.pose.bones[name]
                b = basis_of(pb, mats)
                pb.rotation_mode = 'QUATERNION'
                pb.rotation_quaternion = b.to_quaternion()
                pb.keyframe_insert('rotation_quaternion', frame=f)
                n_keys += 1
        baked.append(new_act.name)
        print("###BAKE_ACTION###", new_act.name, "frames=%d..%d" % (f0, f1),
              "keys=%d" % n_keys)

    # 移除 RT_ 约束（烘焙完即脱离约束系统）
    n_rm = 0
    for pb in miku.pose.bones:
        for c in list(pb.constraints):
            if c.name.startswith("RT_"):
                pb.constraints.remove(c)
                n_rm += 1
    print("###CONSTRAINTS_REMOVED###", n_rm)

    # 自检：烘焙回放 vs 约束态（全部动作 × 采样帧）
    worst_all = 0.0
    for (act_name, f), expected in sorted(check_expected.items()):
        act = bpy.data.actions.get(act_name)
        assign_action(miku, act)
        sc.frame_set(f)
        bpy.context.view_layer.update()
        max_err = 0.0
        worst = ""
        for name in baked_bones:
            m_now = miku.pose.bones[name].matrix.to_3x3()
            m_exp = expected[name].to_3x3()
            ang = math.degrees((m_exp.inverted() @ m_now).to_quaternion().angle)
            if ang > max_err:
                max_err, worst = ang, name
        worst_all = max(worst_all, max_err)
        print("###BAKE_CHECK### %s frame=%d max_err_deg=%.4f worst=%s"
              % (act_name, f, max_err, worst))
    print("###BAKE_CHECK_WORST### %.4f deg" % worst_all)

    # 清空 active action（导出器按下标的 ACTIONS 模式枚举 bpy.data.actions，
    # 不需要也不应该把动作压成 NLA —— 实测 NLA 条会干扰导出采样）
    miku.animation_data.action = None
    for tr in list(miku.animation_data.nla_tracks):
        miku.animation_data.nla_tracks.remove(tr)

    # 导出前清理：只保留 MKI_ 动作 + 删除 CS2 源对象。
    # ⚠️ 实测：glTF 的 ACTIONS 模式会把「所有可绑定动作」都导出——
    #    不清理的话 GLB 里会混入 CS2 的 6 个源动画 + Miku 自带的 2 个（共 14 个）。
    cs2_name = cs2.name
    for a in list(bpy.data.actions):
        if not a.name.startswith("MKI_"):
            bpy.data.actions.remove(a)
    for o in list(bpy.data.objects):
        if o is cs2 or o.name.startswith(cs2_name):
            bpy.data.objects.remove(o, do_unlink=True)
    print("###PURGED_FOR_EXPORT### actions_left=%d" % len(bpy.data.actions))

    # 导出：只选 Miku（骨架 + 网格）
    for o in bpy.data.objects:
        o.select_set(False)
    miku.select_set(True)
    bpy.context.view_layer.objects.active = miku
    n_sel = 1
    for o in bpy.data.objects:
        if o.type == 'MESH' and (o.parent is miku or any(
                m.type == 'ARMATURE' and m.object is miku for m in o.modifiers)):
            o.select_set(True)
            n_sel += 1
    print("###EXPORT_SELECTION###", n_sel)

    if out_glb:
        d = os.path.dirname(out_glb)
        if d:
            os.makedirs(d, exist_ok=True)
        try:
            bpy.ops.export_scene.gltf(
                filepath=out_glb, use_selection=True,
                export_animations=True, export_animation_mode='ACTIONS',
                export_apply=False)
        except TypeError as e:
            print("###GLTF_OPTS_FALLBACK###", e)
            bpy.ops.export_scene.gltf(filepath=out_glb, use_selection=True)
        print("###EXPORT_GLB###", out_glb, os.path.exists(out_glb))

    if out_fbx:
        d = os.path.dirname(out_fbx)
        if d:
            os.makedirs(d, exist_ok=True)
        try:
            bpy.ops.export_scene.fbx(
                filepath=out_fbx, use_selection=True,
                object_types={'ARMATURE', 'MESH'},
                bake_anim=True, bake_anim_use_all_actions=True,
                bake_anim_use_nla_strips=False,
                add_leaf_bones=False,
                global_scale=100.0,
                axis_forward='-Y', axis_up='Z')
        except TypeError as e:
            print("###FBX_OPTS_FALLBACK###", e)
            bpy.ops.export_scene.fbx(filepath=out_fbx, use_selection=True)
        print("###EXPORT_FBX###", out_fbx, os.path.exists(out_fbx))

    print("###BAKED_ACTIONS###", json.dumps(baked, ensure_ascii=False))
    print("###DONE###")


if __name__ == "__main__":
    main()
