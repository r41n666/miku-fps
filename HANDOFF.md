# 交接说明（HANDOFF）· miku-fps

> 最后更新：2026-10-07 23:15
> 用途：在另一台设备上接手本项目。接手前**必读第 2 节（环境）与第 6 节（红线）**。

---

## 1. 项目现状

**miku-fps** —— 类 CS 的 FPS 原型，T/CT 阵营都用 `cat_hatsune_miku.glb`（111 骨），
靠配色/附件区分阵营。动画源用 **CS2 干员模型**（ValveBiped 骨骼）。

### 已完成（全部实测验证）

| 事项 | 结果 |
|---|---|
| 资产核查 | cat 模型 111 骨 / Z-up / **标准 T-pose** / 21 根必需骨零缺失 |
| 骨骼映射表 | 23 根（docs/bone_mapping.md），**21/21 实测映射成功** |
| 重定向链路 | 仿真 CS2 骨架端到端跑通，渲染证实动作迁移生效 |
| Blender 踩坑 | 8 条 API 坑 + 渲染取景坑，全部沉淀（见第 5 节） |

### 判定

**go/no-go = PASS**。剩下的工作是把真实 CS2 干员接进已验证的链路。

### 当前卡点

`cs2_agent.gltf/.bin`（约 1.1GB）已在本机导出，**未入库**（版权 + 体积，见第 6 节）。
新设备需重新导出（第 3 节），然后跑第 4 节的命令。

---

## 2. 环境清单

### 本机（Windows）路径 —— 换设备后路径会变，只作参考

| 工具 | 本机路径 |
|---|---|
| Blender 5.2.2 LTS | `D:\Program Files\Blender Foundation\Blender 5.2\blender.exe` |
| Source 2 Viewer | `C:\Users\Administrator\Desktop\Source2Viewer.exe`（自包含，免安装） |
| CS2 安装目录 | `D:\Program Files\steam\steamapps\common\Counter-Strike Global Offensive\` |
| Godot 4.7.2 | `C:\Users\Administrator\Desktop\Godot_v4.7.2-stable_win64_console.exe` |

### 新设备需要

1. **Blender 4.x 或 5.x**（脚本已做版本兼容，glTF 导入算子自动探测）
2. **Source 2 Viewer**：https://github.com/ValveResourceFormat/ValveResourceFormat/releases
3. **Godot 4.7.2**（后续阶段才用到）
4. Steam 上的 CS2（要提取干员模型）

---

## 3. 在新设备重新导出 cs2_agent

1. 打开 Source 2 Viewer → Game Explorer 自动检测 CS2（或手动开
   `game/csgo/pak01_dir.vpk`）
2. 搜索 `agents/models/ctm_sas`
3. 右键 `.vmdl_c` → **Decompile & Export** → 格式选 **glTF**（分离格式即可，
   本项目的 `.gltf + .bin` 就是这么来的；选 GLB 单文件也行）
4. 导出到 `prototype/`（此目录已 gitignore，不会误入库）
5. **验证导出质量**：在 S2V 里双击模型预览，工具栏动画下拉框应能看到
   idle / run / walk 等序列。看不到动画 → 换一个干员重试（推荐 ctm_sas / ctm_fbi）

> 提示：S2V 有 CLI 批量模式（`Source2Viewer-CLI`），跑通一个后可批量导出全部动画。

---

## 4. 已验证的命令流水线

```bash
BL="<你的 blender 路径>"   # 例: "D:/Program Files/Blender Foundation/Blender 5.2/blender.exe"

# ① 核验模型（骨骼数 / T-pose / 坐标轴 / 必需骨缺失）
"$BL" -b --factory-startup --python blender/verify_asset.py -- prototype/cs2_agent.gltf

# ② 跑重定向（真实干员替换 fake_cs2）
"$BL" -b --factory-startup --python blender/retarget_cs2_to_miku.py -- \
    --cs2 prototype/cs2_agent.gltf \
    --miku assets/characters/cat_hatsune_miku.glb \
    --out prototype/miku_retargeted.glb

# ③ 渲染验证（扫 8 个方位角，找出能看到模型的角度）
"$BL" -b --factory-startup --python blender/render_probe.py -- \
    --cs2 prototype/cs2_agent.gltf \
    --miku assets/characters/cat_hatsune_miku.glb \
    --outdir prototype/render --frame 10

# ④ 量化检查渲染结果（必须！别靠肉眼看深色图）
"$BL" -b --factory-startup --python blender/check_render.py -- --dir prototype/render
```

**第②步预期输出**：`###MAPPED### 21` + `###MISSING### []`。
若 MISSING 非空：脚本会列出真实骨名，把差异补进 `blender/retarget_cs2_to_miku.py`
的 `BONE_MAP`（映射依据见 `docs/bone_mapping.md`）。

---

## 5. 踩坑速查（详情见 docs/validation_report.md）

| 症状 | 原因 | 对策 |
|---|---|---|
| 渲出一张纯深色图 | 方位角不对，差 45° 就完全看不到模型 | 跑 render_probe 扫 8 角度；用 check_render 量化判断 |
| 渲染「成功」但文件不存在 | `-b` 无头下 EEVEE 假成功 | 必须 `CYCLES` + `device='CPU'` |
| 包围盒恒为 ±1 | glTF 导入遗留默认 Cube（不在 glTF_not_exported 集合） | 脚本已自动清；自己写脚本时按「Cube 前缀 + ≤24 顶点」排 |
| 映射全部 MISSING | 骨骼名前缀重复拼接 | 用脚本里现成的 `find_cs2_bone`（剥前缀） |
| `'Bone' has no attribute 'constraints'` | constraints 在 pose bone | `arm.pose.bones[...]` |
| 5.x 导入算子报错 | `wm.gltf_import` 已改名 | 脚本已兼容，别手写 |
| `BLENDER_EEVEE_NEXT not found` | 5.2 枚举改名 | 用 `BLENDER_EEVEE` |
| `cam.data.angle` 算出巨距 | 它是**弧度**不是度数 | `dist = (h/2)/tan(angle/2)` |

**通用纪律**：渲完必须跑 `check_render.py`（bright_ratio > 0.02 才算有内容）；
补丁打两三次仍不对就整个重写文件，别继续 sed。

---

## 6. 版权红线（不可违反）

- ✅ 可以：本机离线提取 CS2 资产 → 本地原型验证
- ❌ **不入库**：`prototype/cs2_agent*`、`prototype/*_psd_*.png`、`*_tga_*.png` 等
  全部 CS2 提取物（.gitignore 已配置）。**换设备时重新导出，不要走网盘/GitHub 传**
- ❌ 不分发、不商用（CS2 资产归 Valve；Miku 形象归 Crypton Future Media）
- ❌ 不注入 CS2 客户端进程（VAC 红线）

---

## 7. 下一步（按序）

1. **新设备**：装 Blender + Source 2 Viewer（第 2 节）→ 重新导出 ctm_sas（第 3 节）
2. 跑第 4 节 ①②，若 MISSING 非空则补 `BONE_MAP`
3. 跑 ③④，肉眼 + 量化确认 5 个动作：idle / run / walk / crouch / death
4. 烘焙动作 → 导出 FBX（Forward=-Y, Up=Z）→ Godot 4.7.2 导入验证
5. Godot 工程搭建（可参考 `Dodoveloper/godot4-fps-prototype` 的压枪弹道）

## 8. 仓库说明

- `assets/` 内的 Miku 模型来自 Sketchfab（作者页面有 CC 许可），武器模型同源；
  `hit_female/` 音效来源为本机既有素材。**公开仓库前请自行核对各项许可**，
  建议**建私有仓库**。
- `blender/` 下 5 个脚本均可独立运行，互不依赖（除 render_check/render_probe
  复用 retarget 的映射表）。
- `prototype/fake_cs2.glb` 是仿真 CS2 骨架（23 骨 + walk 动画），可作回归测试用——
  真实干员跑挂了先用它确认是链路问题还是数据问题。
