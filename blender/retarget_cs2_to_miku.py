"""
骨骼重定向脚本 · CS2 (ValveBiped) → cat_hatsune_miku (MMD)
=============================================================
在 Blender 中运行，把 CS2 角色的动画重定向到 Miku 骨骼上。

用法 A · GUI（交互式调整）
    1. File > Import > glTF 导入 CS2 干员模型（Source 2 Viewer 导出的 .glb）
    2. File > Import > glTF 导入 assets/characters/cat_hatsune_miku.glb
    3. Scripting 工作区，打开本脚本
    4. 按实际对象名修改下方 CS2_MODEL / MIKU_MODEL
    5. Run Script

用法 B · 无头模式（命令行批量，推荐先跑这个）
    blender -b --factory-startup --python retarget_cs2_to_miku.py \
        -- --cs2 <cs2.glb> --miku <miku.glb> --out <output.glb>

⚠️ Blender 版本注意
    5.x 的 glTF 导入算子是 bpy.ops.import_scene.gltf；
    5.x 之前是 bpy.ops.wm.gltf_import。写脚本不要凭记忆，用 hasattr 兜底。

原理
----
为每根 Miku 骨骼添加 COPY_ROTATION 约束，目标是对应部位的 CS2 骨骼。
播放 CS2 动画时 Miku 骨骼跟随，实现动作迁移。
MMD 特有骨（ponytail/ear/mouth）不映射，保持静止。

前置条件（已由 verify_asset.py 实测确认）
    cat_hatsune_miku.glb：111 骨，Z-up，rest pose 为标准 T-pose
"""

import bpy
import sys
import os
import json

# ============================================================
# 配置
# ============================================================
CS2_MODEL = "CS2_Player"         # GUI 模式：CS2 模型对象名
MIKU_MODEL = "cat_hatsune_miku"   # GUI 模式：Miku armature 对象名

# ============================================================
# 骨骼映射表：CS2 骨骼 → Miku 骨骼（Miku 侧带 _NN 序号后缀）
# 依据 docs/bone_mapping.md，已由 Blender 实测校准
# ============================================================
BONE_MAP = {
    "Bip01_Pelvis":       "hips_106",
    "Bip01_Spine":        "spine_95",
    "Bip01_Spine1":       "spine_95",     # 合并到下胸椎
    "Bip01_Spine2":       "chest_94",
    "Bip01_Chest":        "chest_94",     # 与 Spine2 共用
    "Bip01_Neck1":        "neck_50",
    "Bip01_Head1":        "head_49",
    "Bip01_L_Clavicle":   "shoulder.L_69",
    "Bip01_L_UpperArm":   "upper_arm.L_68",
    "Bip01_L_Forearm":    "lower_arm.L_67",
    "Bip01_L_Hand":       "hand.L_66",
    "Bip01_R_Clavicle":   "shoulder.R_88",
    "Bip01_R_UpperArm":   "upper_arm.R_87",
    "Bip01_R_Forearm":    "lower_arm.R_86",
    "Bip01_R_Hand":       "hand.R_85",
    "Bip01_L_Thigh":      "upper_leg.L_100",
    "Bip01_L_Calf":       "lower_leg.L_99",
    "Bip01_L_Foot":       "foot.L_97",
    "Bip01_L_Toe0":       "toes.L_96",
    "Bip01_R_Thigh":      "upper_leg.R_105",
    "Bip01_R_Calf":       "lower_leg.R_104",
    "Bip01_R_Foot":       "foot.R_102",
    "Bip01_R_Toe0":       "toes.R_101",
}

# CS2 侧骨骼名候选。
# ⚠️ BONE_MAP 的键已含 "Bip01_" 前缀，绝不能再用 "Bip01_{}" 模板去 format，
#    否则会拼出 "Bip01_Bip01_Pelvis" 这种双前缀，导致全部映射失败（实测踩过）。
#    正确做法：先剥掉 Bip01_/ValveBiped. 前缀得到裸名，再按精确名 / 后缀匹配。
NAME_PREFIXES = ["ValveBiped.Bip01_", "ValveBiped.", "Bip01_"]

# 不映射的 Miku 骨（装饰/头发/猫耳，保持静止）
SKIP_PREFIX = [
    "ponytail", "ear", "mouth", "eye",
    "lower_arm.L.001", "lower_arm.R.001",
    "lower_leg.L.001", "lower_leg.R.001",
]


# ============================================================
# 工具函数
# ============================================================
def import_gltf(path):
    """Blender 5.x / 4.x 兼容导入"""
    if hasattr(bpy.ops.import_scene, "gltf"):
        return bpy.ops.import_scene.gltf(filepath=path)
    return bpy.ops.wm.gltf_import(filepath=path)


def purge_scene():
    """清掉默认场景的 Cube/Camera/Light，避免污染输出"""
    for name in ("Cube", "Camera", "Light"):
        o = bpy.data.objects.get(name)
        if o:
            bpy.data.objects.remove(o, do_unlink=True)


def find_cs2_bone(arm, base):
    """按骨骼名查找 CS2 侧骨骼，容忍前缀差异。

    base 形如 "Bip01_L_Thigh"。依次尝试：
      1. 精确匹配
      2. 剥掉已知前缀后精确匹配
      3. 后缀匹配（防止 CS2 导出用了别的命名变体）
    """
    existing = {b.name: b for b in arm.data.bones}
    if base in existing:
        return base

    # 剥前缀后匹配
    bare = base
    changed = True
    while changed:
        changed = False
        for p in NAME_PREFIXES:
            if bare.startswith(p):
                bare = bare[len(p):]
                changed = True
                break
    if bare != base and bare in existing:
        return bare

    # 后缀匹配：找一个以裸名结尾的骨
    hits = [n for n in existing if n.endswith(bare)]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        print("  [warn] 后缀匹配到多根骨，需人工确认: %s -> %s" % (base, hits))

    return None


def find_miku_bone(arm, base):
    """查找 Miku 侧骨骼。

    BONE_MAP 里的键带 _NN 序号后缀（如 spine_95），但不同导出版本可能没有
    后缀（如 spine）。所以：精确 → 前缀匹配 → 剥掉 _NN 后缀精确匹配。
    """
    existing = {b.name: b for b in arm.data.bones}
    if base in existing:
        return base

    # 前缀匹配：spine_95 -> spine（唯一时才用，避免歧义）
    pref = base + "_"
    hits = [n for n in existing if n.startswith(pref)]
    if len(hits) == 1:
        return hits[0]

    # 剥掉 _NN 序号后精确匹配：spine_95 -> spine
    bare = base
    if "_" in base:
        bare = base.rsplit("_", 1)[0]
        if bare in existing:
            return bare
        # spine_95 -> spine_（极端情况：名字里本身带下划线）
        hits = [n for n in existing
                if n.rsplit("_", 1)[0] == bare]
        if len(hits) == 1:
            return hits[0]

    return None


# ============================================================
# 核心：建立约束
# ============================================================
def build_constraints(cs2_arm, miku_arm):
    made, missing, duplicated = [], [], []

    for cs2_base, miku_base in BONE_MAP.items():
        miku_name = find_miku_bone(miku_arm, miku_base)
        cs2_name = find_cs2_bone(cs2_arm, cs2_base)

        if miku_name is None:
            missing.append(("MIKU", miku_base))
            continue
        if cs2_name is None:
            missing.append(("CS2", cs2_base))
            continue

        # 同一根 Miku 骨被多次映射时（如 Spine/Spine1 都指向 spine_95），
        # 只保留第一个约束，否则约束栈互相覆盖会导致抖动
        # ⚠️ constraints 挂在 pose bone 上，不是 data.bones（edit bone）上。
        #    写 miku_arm.data.bones[name].constraints 会抛
        #    AttributeError: 'Bone' object has no attribute 'constraints'（实测踩过）。
        pbone = miku_arm.pose.bones[miku_name]
        already = [c for c in pbone.constraints if c.name.startswith("RT_")]
        if already:
            duplicated.append(miku_name)
            continue

        con = pbone.constraints.new('COPY_ROTATION')
        con.name = "RT_" + cs2_base
        con.target = cs2_arm
        con.subtarget = cs2_name
        con.target_space = 'POSE'
        con.owner_space = 'POSE'
        con.mix_mode = 'REPLACE'
        made.append((cs2_name, miku_name))

    return made, missing, duplicated


def report_unmapped(miku_arm):
    """列出既未映射、又不属于已知装饰骨的骨 —— 需人工判断"""
    mapped = set()
    for pb in miku_arm.pose.bones:          # constraints 在 pose bone 上
        if any(c.name.startswith("RT_") for c in pb.constraints):
            mapped.add(pb.name)

    unknown = []
    for b in miku_arm.data.bones:
        n = b.name.lower()
        if b.name in mapped:
            continue
        if any(n.startswith(s.lower()) for s in SKIP_PREFIX):
            continue
        unknown.append(b.name)
    return mapped, unknown


def validate(miku_arm, cs2_arm):
    """T-pose 前置校验：rest pose 不是 T-pose 时重定向必失败"""
    def find(sub):
        for b in miku_arm.data.bones:
            if sub.lower() in b.name.lower():
                return b
        return None

    issues = []
    ul, ur = find("upper_arm.L"), find("upper_arm.R")
    ll = find("upper_leg.L")
    if ul and ur:
        ldx = abs(ul.tail_local.x - ul.head_local.x)
        ldy = abs(ul.tail_local.y - ul.head_local.y)
        if not (ldx > ldy):
            issues.append("手臂未水平展开（T-pose 异常）")
    if ll:
        if abs(ll.tail_local.z - ll.head_local.z) <= abs(ll.tail_local.x - ll.head_local.x):
            issues.append("腿部未垂直向下（T-pose 异常）")
    # 注意：action 挂在 object 上（animation_data.action），不是 armature.data 上。
    # 早期写 cs2_arm.data.actions 会抛 AttributeError —— 实测踩过。
    has_action = False
    ad = getattr(cs2_arm, "animation_data", None)
    if ad is not None and ad.action is not None:
        has_action = True
    if not has_action:
        issues.append("CS2 模型无动画 action —— 检查导出是否含动画")
    return issues


# ============================================================
# 主流程 · GUI
# ============================================================
def main_gui():
    cs2_obj = bpy.data.objects.get(CS2_MODEL)
    miku_obj = bpy.data.objects.get(MIKU_MODEL)

    if cs2_obj is None or miku_obj is None:
        arms = [(o.name, len(o.data.bones)) for o in bpy.data.objects
                if o.type == 'ARMATURE']
        print("[X] 找不到模型对象。请检查脚本顶部 CS2_MODEL / MIKU_MODEL 配置")
        print("    当前 ARMATURE 对象：", arms)
        return

    issues = validate(miku_obj, cs2_obj)
    if issues:
        print("[!] 前置校验发现问题：")
        for i in issues:
            print("    -", i)

    made, missing, dup = build_constraints(cs2_obj, miku_obj)

    print("=" * 62)
    print(" 骨骼重定向约束建立完成")
    print("=" * 62)
    print("成功映射: %d 根" % len(made))
    for c, m in made:
        print("   %-30s -> %s" % (c, m))
    if dup:
        print("\n跳过重复映射的骨: %s" % ", ".join(dup))
    if missing:
        print("\n未找到 (%d):" % len(missing))
        for side, n in missing:
            print("   [%s] %s" % (side, n))

    _, unknown = report_unmapped(miku_obj)
    if unknown:
        print("\n需人工确认的未映射骨 (%d):" % len(unknown))
        print("   " + ", ".join(unknown[:20]))
        if len(unknown) > 20:
            print("   ... 共 %d 根" % len(unknown))

    print("\n下一步：")
    print("  1. 播放 CS2 动作，观察 Miku 是否跟随")
    print("  2. 若骨骼扭曲/错位，在约束 Influence 或轴向旋转上做补偿")
    print("  3. 确认无误后烘焙：全选 Armature → Animation → Bake Action")


# ============================================================
# 主流程 · 无头
# ============================================================
def main_headless():
    argv = sys.argv
    args = argv[argv.index("--") + 1:] if "--" in argv else []

    cs2_path = miku_path = out_path = None
    i = 0
    while i < len(args):
        if args[i] == "--cs2":
            cs2_path = args[i + 1]; i += 2
        elif args[i] == "--miku":
            miku_path = args[i + 1]; i += 2
        elif args[i] == "--out":
            out_path = args[i + 1]; i += 2
        else:
            i += 1

    if not (cs2_path and miku_path):
        print("###ERROR### need --cs2 <path> --miku <path> [--out <path>]")
        return

    purge_scene()

    print("###IMPORT### CS2:", cs2_path)
    import_gltf(cs2_path)
    cs2_arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    if not cs2_arms:
        print("###ERROR### CS2 model has no armature")
        return
    cs2_arm = max(cs2_arms, key=lambda o: len(o.data.bones))
    print("###CS2_ARMATURE###", cs2_arm.name, len(cs2_arm.data.bones))
    print("###CS2_BONES###", json.dumps([b.name for b in cs2_arm.data.bones]))
    # action 挂在 object 上，不是 armature.data 上
    _ad = getattr(cs2_arm, "animation_data", None)
    _act = _ad.action.name if (_ad and _ad.action) else None
    print("###CS2_ACTIONS###", json.dumps(
        [_act] if _act else [], ensure_ascii=False))

    print("###IMPORT### MIKU:", miku_path)
    import_gltf(miku_path)
    miku_arms = [o for o in bpy.data.objects
                 if o.type == 'ARMATURE' and o.name != cs2_arm.name]
    if not miku_arms:
        print("###ERROR### Miku model has no armature")
        return
    miku_arm = miku_arms[0]
    print("###MIKU_ARMATURE###", miku_arm.name, len(miku_arm.data.bones))

    issues = validate(miku_arm, cs2_arm)
    if issues:
        print("###PRECHECK_WARN###", json.dumps(issues, ensure_ascii=False))

    made, missing, dup = build_constraints(cs2_arm, miku_arm)
    print("###MAPPED###", len(made), json.dumps(made, ensure_ascii=False))
    print("###MISSING###", json.dumps(missing, ensure_ascii=False))
    print("###SKIPPED_DUP###", json.dumps(dup, ensure_ascii=False))

    if out_path:
        d = os.path.dirname(out_path)
        if d and not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
        bpy.ops.export_scene.gltf(filepath=out_path)
        print("###EXPORTED###", out_path)

    print("###DONE###")


if __name__ == "__main__":
    if "--" in sys.argv and "--cs2" in sys.argv:
        main_headless()
    else:
        main_gui()