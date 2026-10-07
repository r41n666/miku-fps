# 资产验证报告 · go/no-go 判定

> 执行时间：2026-10-07
> 工具：Blender 5.2.2 LTS（`D:\Program Files\Blender Foundation\Blender 5.2\blender.exe`）
> 判定：**✅ PASS — 骨骼重定向链路已跑通，CS2 动画成功驱动 Miku 模型**

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

- [ ] 真实 CS2 干员模型的骨骼命名未实测（当前用仿真骨架验证链路）
- [ ] CS2 真实动画的轴向/单位与 MMD 不同，可能需要额外的轴向补偿旋转
- [ ] 约束生效时模型整体上移约 1.2 单位（BBOX 从 `z:-0.04..2.98` 变为 `z:1.19..3.65`），
      推测是 MMD 根骨偏移所致，接真实模型后需重新校准原点
- [ ] 手指骨未映射，持枪手势细节可能不足
- [ ] 双马尾/猫耳在重定向后是否被拉伸，需看渲染图确认