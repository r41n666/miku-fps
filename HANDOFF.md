# 交接说明（HANDOFF）· miku-fps

> 最后更新：2026-10-09 11:50（新设备接手 + 真实干员链路跑通）
> 用途：在另一台设备上接手本项目。接手前**必读第 2 节（环境）与第 6 节（红线）**。

---

## 1. 项目现状

**miku-fps** —— 类 CS 的 FPS 原型，T/CT 阵营都用 `cat_hatsune_miku.glb`（111 骨），
靠配色/附件区分阵营。动画源用 **CS2 干员模型**（CS2 新命名骨骼，非 ValveBiped）。

### 已完成（全部实测验证）

| 事项 | 结果 |
|---|---|
| 资产核查 | cat 模型 111 骨 / Z-up / **标准 T-pose** / 21 根必需骨零缺失 |
| 骨骼映射表 | 两套命名（ValveBiped + CS2 新命名），**两套均实测映射成功** |
| 重定向链路 | 仿真骨架 + **真实干员 ctm_sas 均端到端跑通**（MAPPED 21 / MISSING 0） |
| 真实干员渲染验证 | **6 动作（idle/蹲/走/跑/蹲行/跳）渲染通过**，bright_ratio 0.25~0.29 |
| Blender 踩坑 | API/渲染/坐标坑全量沉淀（见第 5 节 + docs/validation_report.md 第九节） |

### 判定

**go/no-go = PASS（真实干员版）**。剩余工作：朝向校验 → 烘焙 → Godot 工程。

### 当前状态

`cs2_agent.glb`（全量 1.1GB / 2091 动画）与精简版 `cs2_agent_anim6.glb`（3.3MB / 6 动作）
均已在本机 `prototype/cs2_agent_export/`（**不入库**，版权 + 体积，见第 6 节）。
新设备重新导出：见第 3 节（已改为 CLI 一条命令）。

---

## 2. 环境清单

### 当前设备（2026-10-09 接手验证）

| 工具 | 当前路径 |
|---|---|
| Blender 5.2.2 LTS | `C:\Tools\Blender\Blender Foundation\Blender 5.2\blender.exe` |
| Source 2 Viewer 20.0 GUI | `C:\Tools\Source2Viewer\Source2Viewer.exe`（自包含，免安装） |
| Source 2 Viewer CLI | `C:\Tools\Source2Viewer\cli\Source2Viewer-CLI.exe` |
| CS2 安装目录 | `C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\` |
| Godot 4.7.2 | `C:\Users\13569\Desktop\Godot_v4.7.2-stable_win64_console.exe` |

**本机无管理员权限时的安装法（已实测）**：
- Blender：`msiexec /a "<msi路径>" /qn TARGETDIR="C:\Tools\Blender"`（管理安装只解包，不需要管理员）
- S2V：github.com 下载被重置/极慢时，用 `https://ghfast.top/<github原始URL>` 镜像（约 600KB/s），
  下载后按官方元数据字节数校验（S2V.exe=105340600、cli-windows-x64.zip=52735867）

### 换新设备需要

1. **Blender 4.x 或 5.x**（脚本已做版本兼容，glTF 导入算子自动探测）
2. **Source 2 Viewer**：https://github.com/ValveResourceFormat/ValveResourceFormat/releases
3. **Godot 4.7.2**（后续阶段才用到）
4. Steam 上的 CS2（要提取干员模型）

---

## 3. 在新设备重新导出 cs2_agent

### 方式 A · CLI（推荐，全自动，已实测）

```bash
CLI="C:/Tools/Source2Viewer/cli/Source2Viewer-CLI.exe"
VPK="C:/Program Files (x86)/Steam/steamapps/common/Counter-Strike Global Offensive/game/csgo/pak01_dir.vpk"

# ① 查文件在 VPK 里的确切路径
"$CLI" -i "$VPK" -f "agents/models/ctm_sas" --vpk_list

# ② 全量导出（~1.1GB，含 2091 个动画；本地存档）
"$CLI" -i "$VPK" -f "agents/models/ctm_sas/ctm_sas.vmdl_c" -d \
    --gltf_export_format glb --gltf_export_animations \
    --gltf_export_materials --gltf_textures_adapt \
    -o "prototype/cs2_agent_export/cs2_agent.glb" --threads 4

# ③ 精简导出（~3.3MB，只含 6 个核心动作；迭代验证用，推荐）
R="animation/anims/world/rifle/_default_rifle"
"$CLI" -i "$VPK" -f "agents/models/ctm_sas/ctm_sas.vmdl_c" -d \
    --gltf_export_format glb --gltf_export_animations \
    --gltf_animation_list "$R/idle_rifle,$R/idle_crouch_rifle,$R/walk_n_rifle,$R/run_n_rifle,$R/crouch_n_rifle,$R/jump_stand_rifle" \
    --gltf_export_materials --gltf_textures_adapt \
    -o "prototype/cs2_agent_export/cs2_agent_anim6.glb" --threads 4
```

**CLI 坑（实测）**：
- `steam:730/...` 路径前缀不被识别（会被当相对路径报错）→ 用绝对路径（正斜杠可）
- `--game <文件夹>` 会报 `does not exist` → **省略即可**（input 在游戏目录内能自动定位 gameinfo.gi）
- 动画清单核验：`prototype/cs2_agent_export/` 下的 `inspect_glb.py` / `filter_anims.py`（本地脚本，不入库）

### 方式 B · GUI（备选）

1. 打开 Source 2 Viewer → 开 `game/csgo/pak01_dir.vpk` → 搜索 `agents/models/ctm_sas`
2. 右键 `.vmdl_c` → **Decompile & Export** → 格式选 **glTF / GLB**
3. 关口验证：S2V 内双击预览，动画下拉框能看到 idle / run / walk 等序列

---

## 4. 已验证的命令流水线

```bash
BL="C:/Tools/Blender/Blender Foundation/Blender 5.2/blender.exe"

# ① 核验模型（骨骼数 / 坐标轴 / 必需骨缺失）
"$BL" -b --factory-startup --python blender/verify_asset.py -- \
    prototype/cs2_agent_export/cs2_agent_anim6.glb

# ② 重定向（含「骨架转正」自动修复；预期 ###MAPPED### 21 + ###MISSING### []）
"$BL" -b --factory-startup --python blender/retarget_cs2_to_miku.py -- \
    --cs2 prototype/cs2_agent_export/cs2_agent_anim6.glb \
    --miku assets/characters/cat_hatsune_miku.glb \
    --out prototype/cs2_agent_export/miku_retargeted_anim6.glb

# ③ 渲染验证（一次会话渲染 6 个动作；--hide-cs2 只显 Miku、--aim 自动对位）
"$BL" -b --factory-startup --python blender/render_check.py -- \
    --cs2 prototype/cs2_agent_export/cs2_agent_anim6.glb \
    --miku assets/characters/cat_hatsune_miku.glb \
    --outdir "C:/miku-fps/miku-fps/prototype/cs2_agent_export/render_final" \
    --hide-cs2 1 --aim 1 --az 45 --elev 5 --dist 3.6 \
    --actions "idle_rifle,idle_crouch_rifle,walk_n_rifle,run_n_rifle,crouch_n_rifle,jump_stand_rifle"

# ④ 量化检查渲染结果（必须！不靠肉眼判断深色图）
"$BL" -b --factory-startup --python blender/check_render.py -- \
    --dir prototype/cs2_agent_export/render_final

# ⑤ 烘焙 → 导出交付资产（GLB 为准；FBX 备选）
"$BL" -b --factory-startup --python blender/bake_retarget.py -- \
    --cs2 prototype/cs2_agent_export/cs2_agent_anim6.glb \
    --miku assets/characters/cat_hatsune_miku.glb \
    --actions "idle_rifle,idle_crouch_rifle,walk_n_rifle,run_n_rifle,crouch_n_rifle,jump_stand_rifle" \
    --out-glb prototype/cs2_agent_export/animated/miku_anim6.glb

# ⑥ 出厂产物回环复检（重导入 + 渲染，验证"最终 glb"里动作真实生效）
"$BL" -b --factory-startup --python blender/verify_baked.py -- \
    --glb prototype/cs2_agent_export/animated/miku_anim6.glb \
    --outdir "C:/miku-fps/miku-fps/prototype/cs2_agent_export/render_baked2" \
    --action walk

# ⑦ Godot 4.7.2 导入验证（详见 tools/godot_import_check/README.md）
#    把 miku_anim6.glb 复制进 tools/godot_import_check/ 后：
#    "godot.exe" --headless --path "<该目录>" --import
#    "godot.exe" --headless --path "<该目录>" --script res://check_anims.gd
```

**第②步预期输出**：`###CS2_UPRIGHT_FIX### applied ...` + `###BONE_MAP_SELECTED### cs2_new(REAL_AGENT)`
+`###MAPPED### 21` +`###MISSING### []`。
**第⑤步预期输出**：`###BAKE_CHECK_WORST### 0.0000 deg`（全部动作 × 首/中/末帧的自检误差）。
若 MISSING 非空：脚本会列出真实骨名，把差异补进 `BONE_MAP_OLD/_NEW`（依据 `docs/bone_mapping.md`）。

> ⚠️ 渲染脚本的 `--outdir` 一律传**绝对路径**（无头模式相对路径会被解析到盘根，见第 5 节）。

---

## 5. 踩坑速查（详情见 docs/validation_report.md）

| 症状 | 原因 | 对策 |
|---|---|---|
| 渲出一张纯深色图 | 方位角不对，差 45° 就完全看不到模型 | 跑 render_probe 扫 8 角度；用 check_render 量化判断 |
| 渲染「成功」但文件不存在 | `-b` 无头下 EEVEE 假成功 | 必须 `CYCLES` + `device='CPU'` |
| 渲染产出跑到 `C:\prototype\...` | 无头模式把**相对 outdir** 解析到当前盘根 | 渲染脚本已强制绝对路径；手写脚本注意同样问题 |
| 包围盒恒为 ±1 | glTF 导入遗留默认 Cube（不在 glTF_not_exported 集合） | 脚本已自动清；自己写脚本时按「Cube 前缀 + ≤24 顶点」排 |
| **Miku 被驱动成「躺姿」** | **S2V 导出的干员骨架导入后整体躺平（rest 骨方向 ≈ -Y）；约束是 armature 空间匹配** | **脚本已内置 `align_cs2_upright()`（转正 + transform_apply 烘焙），无需手动处理** |
| 真实干员 MISSING 一大片 | 干员骨骼命名**不是** ValveBiped（CS2 新命名） | 已内置 `BONE_MAP_NEW` + `select_bone_map()` 自动识别；命名再变则按 MISSING 清单补表 |
| 源网格（士兵）渲染姿态奇怪/腿朝上 | Blender 对「多根节点 skin」导出结构的导入处理问题（文件本身规范） | **不影响骨骼驱动链路**（约束只取骨骼）；源可视化建议用 S2V 预览器 |
| 烘焙自检「全过」但成品不对 | **自检只查了单个静态动作的单帧**（idle@frame0 天然查不出问题） | 自检必须覆盖**全部动作 × 首/中/末帧**；`bake_retarget.py` 已内置（看 `###BAKE_CHECK_WORST###`） |
| FBX 导入 Godot 后极小 / 朝向不对 | Blender FBX 导出单位（≈1/100）与轴向 ≠ Godot 预期 | **交付以 GLB 为准**（已全项验证）；FBX 为实验性备选 |
| 肉眼比对渲染图误判姿态不一致 | 两次会话的相机 aim 中心/相位不同，会造成像素偏移 | 用「已知不同动作」的差异做基线对照：同相位对照差异应显著小于换动作/换帧 |
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

1. ~~新设备装工具链 + 重新导出 ctm_sas~~ ✅ 2026-10-09（环境见第 2 节，导出见第 3 节）
2. ~~跑 ①②，补 BONE_MAP~~ ✅（含「骨架转正」修复：MAPPED 21 / MISSING 0）
3. ~~跑 ③④，确认核心动作~~ ✅（6 动作渲染 + 量化通过；**death 无动画**——CS2 死亡为
   ragdoll 物理，动作集改为 idle / run / walk / crouch / jump，可加 `flinch_*`）
4. ~~朝向校验~~ ✅ 2026-10-11（面朝 = 迈步方向，无翻转；扫描图 `render_sweep/`）
5. ~~烘焙 → 导出 → Godot 4.7.2 导入验证~~ ✅ 2026-10-11
   （`bake_retarget.py`，自检 13 点全 0.0000°；**GLB 全项通过 = 交付格式**，
   FBX 备选；Godot 侧动画驱动骨骼 201.66°，见 `docs/validation_report.md` 第十节）
6. **Godot 工程搭建**（可参考 `Dodoveloper/godot4-fps-prototype` 的压枪弹道）：
   接入 `miku_anim6.glb` + 武器 glb + 音效，做出可玩的射击原型
   ⚠️ 注意事项：当前动画**只含旋转**（骨盆位移未传递）、根骨带固有偏移——
   游戏侧先按「动画原地播放 + 代码驱动位移」的方式使用

## 8. 仓库说明

- `assets/` 内的 Miku 模型来自 Sketchfab（作者页面有 CC 许可），武器模型同源；
  `hit_female/` 音效来源为本机既有素材。**公开仓库前请自行核对各项许可**，
  建议**建私有仓库**。
- `blender/` 下 7 个脚本：retarget / render_check / render_probe / check_render /
  verify_asset / bake_retarget / verify_baked（渲染类脚本复用 retarget 的映射表，
  其余独立）。
- `tools/godot_import_check/`：Godot 导入验证工程（用法见其 README.md）。
- `prototype/fake_cs2.glb` 是仿真 CS2 骨架（23 骨 + walk 动画），可作回归测试用——
  真实干员跑挂了先用它确认是链路问题还是数据问题。
