# 骨骼重定向映射表 · CS2 (ValveBiped) → cat_hatsune_miku (MMD)

> 生成时间：2026-10-07
> 来源：cat_hatsune_miku.glb 二进制实测解析（111 根骨骼全表）+ CS2 骨骼索引表交叉验证

## 为什么要这张表

CS2 角色模型用的是 Valve 骨骼体系，命名形如 `ValveBiped.Bip01_Spine`。
`cat_hatsune_miku.glb` 是 MMD 转换来的，命名形如 `spine_95`、`chest_94`（**带序号后缀**）。
两套命名完全不同，Blender 的骨骼约束（Bone Constraint）需要逐根映射，否则动画会崩。

好消息：cat 模型的骨架是**完整人形**（含 clavicle/upper_arm/lower_arm/hand、upper_leg/lower_leg/foot/toes），
以及额外的 MMD 特征骨（ponytail ×18、ear ×6、mouth ×6、Bone.* 装饰骨 ×26）。
多出来的头发/猫耳/嘴部骨骼在重定向时**保持静止**即可，靠权重 0 挂在头部。

## 核心映射（19 根必需骨）

| CS2 骨骼 | CS2 索引 | cat_hatsune_miku 骨骼 | 备注 |
|---|---|---|---|
| Bip01_Pelvis | 1 | `hips_106` | 根骨，动画根节点 |
| Bip01_Spine | 2 | `spine_95` | 下胸椎 |
| Bip01_Spine1 | 3 | — | 映射到 spine_95（与下胸椎合并） |
| Bip01_Spine2 | 4 | `chest_94` | 上胸椎 |
| Bip01_Chest / Chest | 23 | `chest_94` | 与上胸椎共用 |
| Bip01_Neck1 | 6 | `neck_50` | |
| Bip01_Head1 | 7 | `head_49` | |
| Bip01_L_Clavicle | 8 | `shoulder.L_69` | |
| Bip01_L_UpperArm | 9 | `upper_arm.L_68` | 肩→上臂 |
| Bip01_L_Forearm | 10 | `lower_arm.L_67` | 肘→小臂 |
| Bip01_L_Hand | 11 | `hand.L_66` | |
| Bip01_R_Clavicle | 12 | `shoulder.R_88` | |
| Bip01_R_UpperArm | 13 | `upper_arm.R_87` | |
| Bip01_R_Forearm | 14 | `lower_arm.R_86` | |
| Bip01_R_Hand | 15 | `hand.R_85` | |
| Bip01_L_Thigh | 17 | `upper_leg.L_100` | |
| Bip01_L_Calf | 18 | `lower_leg.L_99` | 膝→小腿 |
| Bip01_L_Foot | 19 | `foot.L_97` | |
| Bip01_L_Toe0 | 20 | `toes.L_96` | |
| Bip01_R_Thigh | 20 | `upper_leg.R_105` | |
| Bip01_R_Calf | 21 | `lower_leg.R_104` | |
| Bip01_R_Foot | 22 | `foot.R_102` | |
| Bip01_R_Toe0 | 22 | `toes.R_101` | |

## 真实 CS2 干员映射表（cs2_new 命名，2026-10-09 ctm_sas 实测）

> ⚠️ 真实干员的骨骼命名**不是** ValveBiped（无 `Bip01_` 前缀），而是 CS2 新命名体系。
> 实测来源：`prototype/cs2_agent_export/cs2_agent.glb`（Source 2 Viewer CLI 导出，94 骨）。
> 映射表已写入 `blender/retarget_cs2_to_miku.py` 的 `BONE_MAP_NEW`，
> 由 `select_bone_map()` 自动识别 —— 实测结果：**MAPPED 21 / MISSING 0**。

| CS2 骨骼（实测名） | Miku 骨骼 | 备注 |
|---|---|---|
| `pelvis` | `hips_106` | 根骨（其上还有 `root_motion`，不映射） |
| `spine_1` | `spine_95` | 4 节脊柱取第 2 节驱动下胸椎 |
| `spine_3` | `chest_94` | 第 4 节（最上）驱动上胸椎 |
| `neck_0` | `neck_50` | |
| `head_0` | `head_49` | |
| `clavicle_L` / `clavicle_R` | `shoulder.L_69` / `shoulder.R_88` | |
| `arm_upper_L` / `arm_upper_R` | `upper_arm.L_68` / `upper_arm.R_87` | |
| `arm_lower_L` / `arm_lower_R` | `lower_arm.L_67` / `lower_arm.R_86` | |
| `hand_L` / `hand_R` | `hand.L_66` / `hand.R_85` | |
| `leg_upper_L` / `leg_upper_R` | `upper_leg.L_100` / `upper_leg.R_105` | |
| `leg_lower_L` / `leg_lower_R` | `lower_leg.L_99` / `lower_leg.R_104` | |
| `ankle_L` / `ankle_R` | `foot.L_97` / `foot.R_102` | |
| `ball_L` / `ball_R` | `toes.L_96` / `toes.R_101` | 脚掌球骨 → 脚趾 |

**不映射的新命名骨**：`root_motion`（根位移）、`spine_0` / `spine_2`（四节脊柱只取两节，
约束为单源复制，多源会互相覆盖）、`scapula_*`（肩胛）、`*_TWIST` / `*_TWIST1`（变形辅助）、
`jiggle_*`（布料/装备抖动）、`scap_*_AIMAT` / `scap_AIMUP`（瞄准层）、`wpnPivot` / `wpn`（武器挂点）、
`eyeball_*` / `eye_target`、全部 `finger_*`。

## 手指骨（CS2 有 5 指 ×3 节，cat 也有，可选映射）

CS2 侧 `Bip01_L_Finger0`（拇指）/ `Finger1`（食指）/ `Finger2`（中指）/ `Finger3`（无名）/ `Finger4`（小指），
cat 侧对应 `thumb_*` / `index_*` / `middle_*` / `ring_*` / `little_*` 各 3 节（proximal/intermediate/distal）。

**建议：不映射手指。** CS2 的持枪姿势由 `Anim_Attachment_RH` 附件骨驱动，手指细节对 FPS 观感无影响，
映射反而增加出错概率。手指保持绑定在 hand 上即可。

## 保持静止的装饰骨（不参与重定向）

- `ponytail.*` ×18（双马尾）→ 挂 `head_49`，权重 0，不受动画影响
- `ear.*` ×6（猫耳）→ 同上
- `mouth.*` ×6 → 同上
- `eye.L_0` / `eye.R_1` → 可映射到 CS2 的 Eye_L/Eye_R（索引 25/26），也可静止
- `Bone.L/R_*` ×26、`Bone.008~012` → 未知装饰骨，先静止观察
- `lower_arm.L.001_108` / `lower_arm.R.001_109` → 副小臂骨（可能是防重叠用），静止
- `lower_leg.L.001_98` / `lower_leg.R.001_103` → 副小腿骨，静止

## Blender 实施步骤

1. 导入 CS2 干员模型（Source 2 Viewer 导出 glTF）， armature 名为 `ValveBiped` 系列
2. 导入 `cat_hatsune_miku.glb`
3. 对上表 23 根骨建立 **Copy Rotation** 约束（或直接烘焙成新动画）
4. 姿势对齐：CS2 模型 T-pose 与 MMD 模型 T-pose 的朝向/比例差异需手动校准
   - 检查：MMD 模型通常 Y-up，CS2 导出可能是 Z-up
   - 建议在 Blender 里先统一为 Y-up 再做约束
5. 逐动画验证：跑（run）、走（walk）、蹲（crouch）、跳（jump）、死亡（death）
6. 导出 FBX → 导入 Godot

## 待验证风险

- [ ] CS2 干员模型的实际骨骼命名是否与上表索引完全一致（需用 Source 2 Viewer 导出后实测确认）
- [ ] cat 模型的 rest pose 是否为标准 T-pose（若不是需先做 rest pose 校正）
- [ ] MMD 模型的骨骼局部轴向与 CS2 差异（这是重定向最容易踩坑的地方）
- [ ] ponytail/ear 骨骼是否会在重定向后被拉伸（需检查权重分配）
