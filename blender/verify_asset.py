"""
Pre-flight 验证脚本 · 在 Blender 无头模式（-b）下核验资产
=========================================================
用途：不打开 GUI，纯命令行核验 glTF 资产能否用于骨骼重定向。

用法：
    blender -b --factory-startup --python verify_asset.py -- <file.glb> [file2.glb ...]

输出：ARMATURES / MESHES / T_POSE_TEST / ANIM_ACTIONS 等标记行，
      可用 grep 提取，也可直接人眼阅读。

适配：Blender 5.x（glTF 导入算子为 bpy.ops.import_scene.gltf，
      5.x 之前是 bpy.ops.wm.gltf_import —— 不要凭记忆写算子名）
"""

import bpy
import sys
import json


def load_targets():
    argv = sys.argv
    if "--" not in argv:
        return []
    return argv[argv.index("--") + 1:]


def import_files(paths):
    ok, fail = [], []
    for p in paths:
        try:
            # Blender 5.x 用 import_scene.gltf；旧版本是 wm.gltf_import
            if hasattr(bpy.ops.import_scene, "gltf"):
                bpy.ops.import_scene.gltf(filepath=p)
            else:
                bpy.ops.wm.gltf_import(filepath=p)
            ok.append(p)
        except Exception as e:
            fail.append((p, str(e)))
    return ok, fail


def rest_pose_report(arm):
    """判断 rest pose 是否为标准 T-pose，并报告 Z-up / Y-up"""
    B = arm.data.bones
    names = [b.name for b in B]

    def find(sub):
        for n in names:
            if sub.lower() in n.lower():
                return n
        return None

    def vec(b, attr):
        return [round(v, 4) for v in getattr(b, attr)]

    out = {"total_bones": len(names)}

    # --- 坐标轴朝向判定：看脊柱链是沿 Z 还是 Y 递增 ---
    spine = find("spine_")
    head = find("head_")
    hips = find("hips_")
    axis = None
    if spine and head and hips:
        dz = B[head].head_local.z - B[hips].head_local.z
        dy = B[head].head_local.y - B[hips].head_local.y
        axis = "Z-up" if abs(dz) > abs(dy) else "Y-up"
    out["up_axis"] = axis

    # --- T-pose 判定：双臂是否水平对称展开 ---
    ul, ur = find("upper_arm.L"), find("upper_arm.R")
    if ul and ur:
        lh, lt = B[ul].head_local, B[ul].tail_local
        rh, rt = B[ur].head_local, B[ur].tail_local
        # 手臂方向向量的 X 分量绝对值占比 = 水平程度
        ldx = abs(lt.x - lh.x)
        ldy = abs(lt.y - lh.y)
        ldz = abs(lt.z - lh.z)
        rdx = abs(rt.x - rh.x)
        rdy = abs(rt.y - rh.y)
        rdz = abs(rt.z - rh.z)
        out["arm_L_dir"] = [round(ldx, 4), round(ldy, 4), round(ldz, 4)]
        out["arm_R_dir"] = [rdx, rdy, rdz]
        # 水平展开 = 沿 X 的分量占主导
        out["arms_horizontal"] = (ldx > ldy and ldx > ldz and rdx > rdy and rdx > rdz)
        # 左右对称（X 符号相反）
        out["arms_symmetric"] = ((lt.x - lh.x) * (rt.x - rh.x) < 0)
        out["arm_spread"] = round(abs(lt.x - rt.x), 4)

    # --- 腿部判定：是否垂直向下 ---
    ll, lr = find("upper_leg.L"), find("upper_leg.R")
    if ll and lr:
        lh, lt = B[ll].head_local, B[ll].tail_local
        rh, rt = B[lr].head_local, B[lr].tail_local
        out["leg_L_dir"] = [round(lt.x - lh.x, 4), round(lt.y - lh.y, 4), round(lt.z - lh.z, 4)]
        out["legs_vertical"] = (abs(lt.z - lh.z) > abs(lt.x - lh.x))
        out["leg_spread"] = round(abs(lt.x - rt.x), 4)

    # --- 关键骨存在性（重定向映射表的 23 根）---
    required = [
        "hips", "spine", "chest", "neck", "head",
        "shoulder.L", "upper_arm.L", "lower_arm.L", "hand.L",
        "shoulder.R", "upper_arm.R", "lower_arm.R", "hand.R",
        "upper_leg.L", "lower_leg.L", "foot.L", "toes.L",
        "upper_leg.R", "lower_leg.R", "foot.R", "toes.R",
    ]
    present, missing = [], []
    for r in required:
        (present if find(r) else missing).append(r)
    out["required_present"] = len(present)
    out["required_missing"] = missing

    # --- 规模 ---
    out["max_bone_length"] = round(
        max((b.tail_local - b.head_local).length for b in B), 4)
    return out


def main():
    paths = load_targets()
    if not paths:
        print("###ERROR### no input files given")
        return

    print("###INPUT###")
    for p in paths:
        print("FILE:", p)

    ok, fail = import_files(paths)
    for p, e in fail:
        print("###IMPORT_FAILED###", p, e)
    if not ok:
        print("###ERROR### all imports failed")
        return

    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]

    print("###ARMATURES###", json.dumps(
        [(o.name, len(o.data.bones)) for o in arms], ensure_ascii=False))
    print("###MESHES###", json.dumps(
        [(o.name, len(o.data.vertices)) for o in meshes], ensure_ascii=False))
    print("###ANIM_ACTIONS###", json.dumps(
        [(ac.name, [round(f, 2) for f in ac.frame_range])
         for ac in bpy.data.actions], ensure_ascii=False))

    for a in arms:
        rep = rest_pose_report(a)
        print("###REST_POSE###", a.name, json.dumps(rep, ensure_ascii=False))
        if rep.get("required_missing"):
            print("###WARNING### missing required bones:",
                  rep["required_missing"])
        if rep.get("arms_horizontal") and rep.get("legs_vertical"):
            print("###VERDICT### T-POSE OK - ready for retarget")

    print("###DONE###")


if __name__ == "__main__":
    main()