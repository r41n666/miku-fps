# 资产验证报告 · go/no-go 判定

> 执行时间：2026-10-07
> 工具：Blender 5.2.2 LTS（`D:\Program Files\Blender Foundation\Blender 5.2\blender.exe`）
> 判定：**✅ PASS — 骨骼重定向链路已跑通，CS2 动画成功驱动 Miku 模型**
>
> ⚠️ **2026-10-09 更新**：真实干员 `ctm_sas` 端到端验证已在新设备完成
> （MAPPED 21/21、6 动作渲染通过）——详见文末「九、真实干员验证」。本文档
> 前半部分为仿真骨架阶段记录，保留作回归依据。

---

## 一、核心结论

用一份仿真 CS2 骨架（23 根 ValveBiped 命名骨骼 + walk 动画）作为占位，
完整跑通了「CS2 动画 → Copy Rotation 约束 → Miku 骨骼」的重定向链路。

**实测证据**（`prototype/render/frame_*.png`）：

| 帧 | bright_ratio | 说明 |
|---|---|---|
| frame_001 | 0.080 | 起始姿态 |
| frame_010 | **0.104** | 中间帧，亮像素比首帧多 30% ⇒ 模型姿态确实在变化 |
| frame_020 | 0.080 | 回到起始 |

渲染图 `frame_010.png` 中模型呈现**非 T-pose 的动态姿态**：腿部抬起、身体前倾、双马尾因运动甩起。

> 说明：本次用的是**仿真骨架**，目的是验证工具链路与映射表正确。
> 换成真实的 CS2 干员模型后，动作内容会不同，但链路已验证可用。

---

## 二、模型硬指标（Blender 实测）

| 指标 | cat_hatsune_miku.glb | miku.glb（备份） |
|---|---|---|
| 骨骼数 | **111** | 0 |
| 动画数 | 2（ArmatureAction / idle） | 0 |
| 网格数 | 14 | 14 |
| 顶点数 | 36,584 | — |
| 坐标轴 | **Z-up** | — |
| rest pose | **标准 T-pose** | — |
| 21 根必需骨 | **全部存在，零缺失** | — |

### T-pose 实测数据

```
upper_arm.L:  head(0.0996, 0.0, 1.1653) → tail(0.3175, 0.0087, 1.1578)
upper_arm.R:  head(-0.0996, 0.0, 1.1653) → tail(-0.3175, 0.0087, 1.1578)
⇒ 左右手臂沿 ±X 水平对称展开
upper_leg.L:  z 从 0.7623 降到 0.4321（垂直向下）
⇒ 双腿沿 Z 垂直
```

**这是 CS2 动画重定向的必要条件**（CS2 动画以 T-pose 为源姿态）。Miku 模型满足。

---

## 三、骨骼映射验证结果

**21/21 映射成功，MISSING 为空。**

| CS2 骨骼 | Miku 骨骼 |
|---|---|
| Bip01_Pelvis | hips_106 |
| Bip01_Spine | spine_95 |
| Bip01_Spine2 / Chest | chest_94 |
| Bip01_Neck1 | neck_50 |
| Bip01_Head1 | head_49 |
| Bip01_L_Clavicle | shoulder.L_69 |
| Bip01_L_UpperArm | upper_arm.L_68 |
| Bip01_L_Forearm | lower_arm.L_67 |
| Bip01_L_Hand | hand.L_66 |
| Bip01_R_* | shoulder.R_88 / upper_arm.R_87 / lower_arm.R_86 / hand.R_85 |
| Bip01_L_Thigh | upper_leg.L_100 |
| Bip01_L_Calf | lower_leg.L_99 |
| Bip01_L_Foot | foot.L_97 |
| Bip01_L_Toe0 | toes.L_96 |
| Bip01_R_Thigh / Calf / Foot / Toe0 | upper_leg.R_105 / lower_leg.R_104 / foot.R_102 / toes.R_101 |

**刻意不映射的骨**：`spine_95` 与 `chest_94` 各只接受一个驱动源
（`Bip01_Spine1` 和 `Bip01_Chest` 与它们指向同骨，重复映射会导致约束栈互相覆盖而抖动），
以及 24 根手指骨、18 根 ponytail、6 根猫耳、6 根嘴部装饰骨（保持静止）。

---

## 四、Blender 5.x API 踩坑记录（全部实测修正）

| # | 现象 | 根因 | 正解 |
|---|---|---|---|
| 1 | `could not be found` | 5.x 的导入算子从 `bpy.ops.wm.gltf_import` 改为 `bpy.ops.import_scene.gltf` | 用 `hasattr(bpy.ops.import_scene, "gltf")` 兜底 |
| 2 | `'Armature' object has no attribute 'actions'` | action 挂在 **object** 上（`animation_data.action`），不是 `armature.data` | 取 `obj.animation_data.action` |
| 3 | `'Bone' object has no attribute 'constraints'` | constraints 在 **pose bone** 上，不是 `data.bones`（edit bone） | 用 `arm.pose.bones[name].constraints` |
| 4 | 映射全部失败（MISSING 23 项） | `BONE_MAP` 键已含 `Bip01_`，再用 `"Bip01_{}".format()` 拼出 `Bip01_Bip01_Pelvis` | 先剥前缀再精确匹配 |
| 5 | `enum "BLENDER_EEVEE_NEXT" not found` | 5.2 枚举是 `BLENDER_EEVEE` | 用 `BLENDER_EEVEE` |
| 6 | `blender -b` 渲染「报告成功但文件不落盘」 | EEVEE 需要 GL 上下文，无头模式不可用 | **必须用 `CYCLES` + `device='CPU'`** |
| 7 | 包围盒恒为 `min=[-1,-1,-1]` | glTF 导入遗留默认 `Cube`（**不在** `glTF_not_exported` 集合里，按集合过滤排除不掉），其 bound_box 恰是 ±1 | 双重排除：`glTF_not_exported` 集合 **或** （名字以 Cube 开头且顶点数 ≤ 24） |
| 8 | 相机距离算出 300+ 倍 | `cam.data.angle` 返回**弧度**不是度数，误当度数用了 | `dist = (h/2) / tan(angle/2)` |

---

## 五、渲染取景踩坑（最隐蔽的一类）

这一类问题的共同表现：**渲出一张纯深色背景图，误判为「模型丢了 / 渲染坏了」**。
实际上模型、材质、约束全部正常，只是相机没对着它。

### 关键发现：方位角差 45° 就完全看不到模型

固定 `loc=(2.5,-3.5,1.6)` + `rot_x=80°`，只扫 `rot_z`：

| rot_z | bright_ratio |
|---|---|
| **45°** | **0.1622（可见）** |
| 0° / 90° / 135° / 180° / 225° / 270° / 315° | 0.0000（纯背景） |

⇒ **不要用公式"推导"方位角，必须扫 8 个方位角找正面。**

### 必须用量化的方式判断，别靠肉眼

深蓝灰背景 `(0.04,0.05,0.06)` 在低阈值下会被算作"非黑"。
用 `check_render.py` 的 `bright_ratio`（亮像素 > 0.35 的占比）判断：

```
bright_ratio > 0.02  → 有内容，渲成功了
bright_ratio = 0.00  → 纯背景，模型没进画面
实测：有内容 0.08~0.20，纯背景 0.00
```

### 骨架包围盒不能用于取景

Miku 模型的 `root_107` 根骨带偏移，骨架包围盒 X 方向跑到 **3.641**，
而网格实际只有 `x ∈ [-0.68, 0.68]`。按骨架取景会把相机放到 4 倍远。
⇒ **必须遍历真实顶点**（并排除辅助网格）计算包围盒。

---

## 六、已交付的可复用脚本

| 脚本 | 用途 |
|---|---|
| `blender/verify_asset.py` | 资产核验：骨骼数、动画数、T-pose 判定、坐标轴、必需骨缺失检查 |
| `blender/retarget_cs2_to_miku.py` | 建立 21 根 Copy Rotation 约束，支持 GUI 与无头两种模式 |
| `blender/render_check.py` | 渲染指定帧，验证动作是否生效 |
| `blender/render_probe.py` | 扫 8 个方位角，用于确定模型正面朝向 |
| `blender/check_render.py` | 用 bright_ratio 量化判断渲染图有无内容 |

### 常用命令

```bash
BL="D:/Program Files/Blender Foundation/Blender 5.2/blender.exe"

# 核验资产
"$BL" -b --factory-startup --python blender/verify_asset.py -- \
    assets/characters/cat_hatsune_miku.glb

# 建立重定向约束并导出
"$BL" -b --factory-startup --python blender/retarget_cs2_to_miku.py -- \
    --cs2 <cs2.glb> --miku assets/characters/cat_hatsune_miku.glb \
    --out prototype/miku_retargeted.glb

# 渲染验证
"$BL" -b --factory-startup --python blender/render_check.py -- \
    --cs2 <cs2.glb> --miku assets/characters/cat_hatsune_miku.glb \
    --outdir prototype/render --frames 1,10,20

# 量化检查渲染结果
"$BL" -b --factory-startup --python blender/check_render.py -- \
    --dir prototype/render
```

---

## 七、下一步

**用真实的 CS2 干员模型替换仿真骨架。**

1. 打开 Source 2 Viewer（`C:\Users\Administrator\Desktop\Source2Viewer.exe`）
2. 打开 CS2 的 `game/csgo/pak01_dir.vpk`
3. 搜索 `agents/models/ctm_sas`（或其他干员）
4. 右键 `.vmdl_c` → Decompile & Export → 格式选 **glTF**
5. 导出到 `prototype/cs2_agent.glb`
6. 用上面的命令替换 `--cs2` 参数重跑

**若 CS2 模型的骨骼名与映射表不符**，脚本会打印 `###MISSING###` 清单，
把实际骨名补进 `retarget_cs2_to_miku.py` 的 `BONE_MAP` 即可。

---

## 八、遗留风险

- [x] ~~真实 CS2 干员模型的骨骼命名未实测（当前用仿真骨架验证链路）~~
      → **2026-10-09 已实测：命名与 ValveBiped 完全不同，见第九节**
- [x] ~~CS2 真实动画的轴向/单位与 MMD 不同，可能需要额外的轴向补偿旋转~~
      → **2026-10-09 已实测：需要「骨架转正」修复，见第九节**
- [ ] 约束生效时模型整体上移约 1.2 单位（BBOX 从 `z:-0.04..2.98` 变为 `z:1.19..3.65`），
      推测是 MMD 根骨偏移所致，接真实模型后需重新校准原点
- [ ] 手指骨未映射，持枪手势细节可能不足
- [ ] 双马尾/猫耳在重定向后是否被拉伸，需看渲染图确认

---

## 九、真实干员验证（2026-10-09，新设备，ctm_sas）

> 判定：**✅ PASS — 真实 CS2 干员动画成功驱动 Miku**。
> 环境：Blender 5.2.2（`C:\Tools\Blender\...`）+ Source 2 Viewer **CLI** 20.0（全命令行化）。
> 资产：`agents/models/ctm_sas/ctm_sas.vmdl_c` → `prototype/cs2_agent_export/cs2_agent_anim6.glb`（3.3MB，含 6 个世界动作）。

### 9.1 关键发现一：真实干员骨骼命名 ≠ ValveBiped

实测 ctm_sas 为 **CS2 新命名体系**（无 `Bip01_` 前缀）：

```
pelvis / spine_0..3 / neck_0 / head_0 / clavicle_L / arm_upper_L /
arm_lower_L / hand_L / leg_upper_L / leg_lower_L / ankle_L / ball_L …（94 骨）
```

- 修复：`retarget_cs2_to_miku.py` 新增 `BONE_MAP_NEW`（21 根映射），
  并由 `select_bone_map()` 按实际骨名**自动识别**（旧 ValveBiped 保留作回归）。
- 结果：**`###MAPPED### 21` + `###MISSING### []` + `###DUP### []`**。
- 脊柱取骨策略：`spine_95 ← spine_1`（下段）、`chest_94 ← spine_3`（上段）；
  `spine_0/2` 不驱动（约束为单源复制，多源互相覆盖）。

### 9.2 关键发现二：「躺平」问题（本阶段最大的坑）

**现象**：S2V 导出的干员 glb 导入 Blender 后，整具骨架是「躺平」状态——
pelvis/spine/head 的 rest 骨方向 ≈ 世界 **-Y**（腿 ≈ +Y）。约束执行的是
**armature 空间**朝向匹配（实测：转对象无效、只认骨架数据），
⇒ 直接跑约束，Miku 被驱动成**躺姿**（首轮渲染已复现）。

**修复**（`retarget_cs2_to_miku.py` → `align_cs2_upright()`，幂等）：

```
对象级旋转（rest 骨方向 → +Z）+ bpy.ops.object.transform_apply(rotation=True)
```

把转正烘焙进骨骼数据；局部动画值不变，蒙皮/世界结果不破坏。
**验证**：修复后 Miku 与 CS2 的 5 组关键骨世界方向逐项一致
（pelvis / spine / arm / leg / head，数值级吻合，归一化后完全相同）。

### 9.3 渲染验证（6 动作，`prototype/cs2_agent_export/render_final/`）

| 动作 | bright_ratio | 姿态判读（人工） |
|---|---|---|
| idle_rifle | 0.2533 | 站立持枪待机（前倾） |
| idle_crouch_rifle | 0.2534 | 低姿持枪 |
| walk_n_rifle | 0.2668 | 跨步前进（持枪位） |
| run_n_rifle | 0.2722 | 前倾冲刺 |
| crouch_n_rifle | 0.2898 | 深蹲 |
| jump_stand_rifle | 0.2516 | 腾空收腿 |

渲染参数：`--hide-cs2 1 --aim 1 --az 45 --elev 5 --dist 3.6`（`--aim` 为本次新增的
自动对准相机模式）。判定标准：bright_ratio > 0.02 → 全过（6/6）。

### 9.4 其他实测结论

- **无 death 动画**：`die/dead/ragdoll/dying/death` 关键字均 0 命中——CS2 玩家死亡
  是 ragdoll 物理，无关键帧死亡动画。5 动作集调整为 **idle / run / walk / crouch / jump**，
  可另选 `flinch_*`（45 条受击反应）补充。
- **动画命名**：世界（第三人称）动作为 `animation/anims/world/<weapon>/...`；
  步枪集示例：`idle_rifle / idle_crouch_rifle / walk_n_rifle / run_n_rifle /
  crouch_n_rifle / jump_stand_rifle`（`_n` = 朝北）。
- **源网格在 Blender 中渲染异常**：cs2 士兵网格在 Blender 里呈「绑定位移」状
  （腿朝上等）。经查：GLB 文件本身是规范 Y-up 站立（mesh 沿 Y 2 米），
  疑似 Blender 对「多根节点 skin 导出结构」的导入处理问题；
  **不影响重定向链路**（约束只取骨骼数据，骨骼数学已验证一致）。
  如需源网格可视化，建议用 S2V 自带预览器确认。

### 9.5 本次交付的脚本改动（`blender/`）

| 文件 | 改动 |
|---|---|
| `retarget_cs2_to_miku.py` | + `BONE_MAP_NEW` / `select_bone_map()` / `align_cs2_upright()`；修 `MISSING` 判断链路 |
| `render_check.py` | + `--hide-cs2` / `--hide-miku` / `--actions`（单会话多动作）/ `--aim` 自动对位；outdir 强制绝对路径 |
| `render_probe.py` | outdir 强制绝对路径（无头模式下相对路径会被解析到盘根） |
| `check_render.py` | `--dir` 强制绝对路径（同因） |

### 9.6 遗留事项（下一阶段）

- [ ] **朝向校验**：miku 迈步方向与面朝是否一致（walk_n 朝北）；如需修正，
      在转正环节追加绕 Z 的 180°（或改对齐基准轴）。
- [ ] **骨盆位移未传递**：当前只做旋转（Copy Rotation）；蹲姿高度、跳跃升腾、
      行走起伏来自腿部弯折，无根位移。后续烘焙时考虑叠加 pelvis 平移。
- [ ] **扭转校准**：绝对朝向匹配含 roll；如手臂/腿出现轴向扭转，
      按骨加常量补偿（渲染图上暂未发现明显扭转）。
- [ ] **全量动画集**：全量导出（2091 动画,1.1GB）已在本机 `prototype/`（不入库）；
      进 Godot 前需按玩法选型（移动/射击/换弹等 ~20 条）。
- [ ] **烘焙 → FBX → Godot**：下一步按 `docs/next_steps.md` 第六节执行。

---

## 十、烘焙与 Godot 导入验证（2026-10-11）

> 判定：**✅ PASS —— 重定向动画已烘焙为独立资产，GLB 通过 Godot 4.7.2 全项导入验证**。
> 脚本：`blender/bake_retarget.py`（新增）、`blender/verify_baked.py`（新增）、
> `tools/godot_import_check/`（新增验证工程）。

### 10.1 烘焙（bake_retarget.py）

把「约束驱动」的实时重定向**逐帧烘焙**为 Miku 自己的动作（Godot 不认识 Blender 约束）：

- 原理：逐帧读取约束求值后的 pose matrix → 反解 basis（局部旋转）→ 写入新 Action
  （只烘焙被约束的 21 根骨）；完成后移除 RT_ 约束（否则实时约束会覆盖烘焙结果）
- **自检（关键）**：全部 6 个动作 × 首/中/末帧 = **13 个采样点，约束态 vs 烘焙回放
  最大误差 0.0000°**
- ⚠️ 教训：初版自检只查了 1 个静态动作的 1 帧（idle@frame0），完全无法暴露问题——
  自检必须覆盖**多动作 × 多帧**（已固化进脚本，输出 `###BAKE_CHECK_WORST###`）

### 10.2 交付产物（`prototype/cs2_agent_export/animated/`，本地不入库）

| 文件 | 大小 | 说明 |
|---|---|---|
| `miku_anim6.glb` | 3.7MB | **交付格式**：6 动画 / 111 骨 / 贴图内嵌 |
| `miku_anim6.fbx` | 7.2MB | 备选：动画数据正常，但 Godot 中 scale≈1/100 + Z-up（见 10.4） |

### 10.3 Godot 4.7.2 导入验证（GLB，全项通过）

| 检查项 | 结果 |
|---|---|
| 动画列表 | 6 个，名称精确（`MKI_idle_rifle` … `MKI_jump_stand_rifle`） |
| 骨骼 | Skeleton3D，111 骨 |
| rest 骨骼位置 | 脚 Y=0 / 髋 Y=0.69 / 头 Y=1.24 / 手 ±0.55 → **标准 T-pose、Y-up、尺度正确** |
| 轨道路径 | `GLTF_created_0/Skeleton3D:<骨名>` 全部可解析 |
| 轨道数据 | walk 每轨 ~30 键，键值变化显著（lower_leg 0.62 rad） |
| **动画驱动** | seek 采样：5 根探针骨旋转总变化 **201.66°** → 动画真实驱动骨骼 |
| 出厂回环 | `verify_baked.py` 重导入成品 glb 渲染 walk 两相位 |
| 像素对照 | 同相位 约束态 vs 烘焙态 = 0.033/9.9%，**小于**「换动作」基线（0.055~0.109）和「同动作换帧」（0.072）→ 烘焙 = 约束同姿态 |

### 10.4 其他实测结论

- **FBX 现状**：动画列表/骨骼/驱动均正常（201.58°），但 Godot 导入后 scale≈1/100、
  朝向 Z-up（rest 头骨在 Z 轴）⇒ 暂不作为交付格式。如需修：导出侧调单位/轴向，
  或导入侧补 scale。**Godot 场景用 GLB 即可，无 FBX 依赖**。
- **朝向校验**（§7.4 遗留项）：8 方位角扫描（`render_sweep/`）确认
  **面朝 = 迈步方向**（walk_n 朝北），无 180° 翻转，不需要修正。
- **残留偏移**：动画中角色整体有垂直偏移（约束阶段的固有根骨偏移 + 骨盆位移
  未传递）。进 Godot 后按「动画原地播放 + 代码驱动位移」使用；如需要贴地，
  后续可在烘焙时叠加骨盆位移校正。