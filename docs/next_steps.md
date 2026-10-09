# 下一步操作指南 · 资产验证阶段

> 目标：在投入 Godot 工程开发之前，先验证「CS2 动画能否重定向到 Miku 骨骼」。
> 这是整个项目的 **go/no-go 关口**。
>
> ✅ **2026-10-09：关口已通过（真实干员版）。** 工具链已装、真实干员 ctm_sas 端到端
> 跑通（MAPPED 21 / MISSING 0，6 动作渲染通过）。本文档保留作操作参考；
> 最新状态与下一步请看 `HANDOFF.md` 第 7 节与 `docs/validation_report.md` 第九节。

## 当前进度

| 步骤 | 状态 | 说明 |
|---|---|---|
| 资产核查 | ✅ 完成 | 见 `docs/preflight_report.md` |
| 骨骼映射表 | ✅ 完成 | 见 `docs/bone_mapping.md`（双命名：ValveBiped + CS2 新命名） |
| 重定向脚本 | ✅ 完成 | `blender/retarget_cs2_to_miku.py`（含自动选表 + 骨架转正） |
| 工具链安装 | ✅ 完成 | 新设备 2026-10-09 安装（路径见 `HANDOFF.md` 第 2 节） |
| **动画验证** | ✅ **通过** | 真实干员 6 动作渲染验证（见 `docs/validation_report.md` 第九节） |

## 第一步：安装 Blender（无需联网）

安装包已在本地：`C:\Users\Administrator\Downloads\blender-5.2.2-windows-x64.msi`（364MB，已校验为有效 MSI）

**方式 A · 脚本安装（推荐）**
右键 `tools/setup_blender.bat` → 以管理员身份运行

**方式 B · 手动安装**
双击该 MSI 文件，按向导默认选项安装

**方式 C · 直接命令行**
```bash
msiexec /i "C:\Users\Administrator\Downloads\blender-5.2.2-windows-x64.msi" /qn /norestart
```

安装后验证：
```bash
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --version
```

## 第二步：获取 Source 2 Viewer（需联网）

⚠️ 当前环境 github.com 无法访问，需你在浏览器中手动下载：

1. 打开 https://github.com/ValveResourceFormat/ValveResourceFormat/releases
2. 下载最新 release 的 Windows 版本（自包含包，含 .NET 运行时）
3. 解压到 `C:\Tools\Source2Viewer\`

> 本机已有 .NET（`C:\Program Files\dotnet\dotnet.exe`），若下载的是 framework-dependent
> 版本也能直接运行。

## 第三步：导出 CS2 干员模型

1. 启动 Source 2 Viewer
2. Game Explorer 自动检测到 CS2 → 打开 `game/csgo/pak01_dir.vpk`
3. 搜索 `agents/models/ctm_sas`（或任意干员，推荐从 SAS 开始——最标准的军装模型）
4. 右键 `.vmdl_c` 文件 → **Decompile & Export** → 格式选 **glTF**
5. 导出到 `miku-fps/prototype/cs2_agent.glb`

**⚠️ 关口判定**：导出后在 S2V 内双击预览该模型，检查工具栏动画下拉框：
- ✅ 有动画列表（idle / run / walk 等）→ 继续第四步
- ❌ 无动画或报错 → **停止**，切换 Mixamo 备选方案（见文末）

## 第四步：运行重定向

1. 打开 Blender → Scripting 工作区
2. 导入 `assets/characters/cat_hatsune_miku.glb`
3. 导入 `prototype/cs2_agent.glb`
4. 在文本编辑器打开 `blender/retarget_cs2_to_miku.py`
5. 按实际对象名修改脚本顶部 `CS2_MODEL` / `MIKU_MODEL` 配置
6. 点击 **Run Script**

预期输出：
```
============================================================
骨骼重定向约束建立完成
============================================================
成功映射: 23 根
   ValveBiped.Bip01_Pelvis         -> hips_106
   ValveBiped.Bip01_Spine          -> spine_95
   ...
```

若「未找到」列表非空，说明 CS2 骨骼命名与预期不符，把实际名称补充进脚本的
`NAME_CANDIDATES` 或直接改 `BONE_MAP`。

## 第五步：验证动作（5 个核心动作）

在 Blender 时间轴播放 CS2 动画，逐项检查 Miku 模型：

- [ ] **idle** — 站立待机，无骨骼抖动
- [ ] **run** — 跑步，手臂摆动自然（重点看肘部 `lower_arm`）
- [ ] **walk** — 走路
- [ ] **crouch** — 下蹲，膝盖无翻转
- [ ] **jump** — 跳跃
- [ ] **death** — 死亡倒地

**常见问题与对策**：

| 现象 | 原因 | 对策 |
|---|---|---|
| 手臂扭曲 | 局部轴向差异 | 调整对应骨骼的 Copy Rotation 约束 → 补旋转（X/Y/Z ±90°） |
| 模型整体错位 | 朝向不一致（CS2 Z-up vs MMD Y-up） | 导入后统一旋转到 Y-up |
| 头/胸变形 | Spine 合并冲突 | 检查 `spine_95` 与 `chest_94` 是否被两个约束同时驱动 |
| 双马尾/猫耳拉伸 | 权重继承 | 检查 armature 修改器权重，装饰骨权重置 0 |
| T-pose 不变 | 约束未生效 | 确认已选中 Miku 的 Armature 而非 Mesh；检查 Outliner 层级 |

## 第六步：烘焙与导出（验证通过后）

1. 选中 Miku 的 Armature → `Ctrl+A` 全选动作
2. 菜单 `Animation` → `Bake Action`（烘焙为独立动作，脱离 CS2 模型）
3. 确认装饰骨保持静止后导出：`File` → `Export` → `FBX`
   - 勾选 `Bake Animation`
   - 轴向设置：Forward `-Y`，Up `Z`（Godot 兼容设置）
4. 导出为 `assets/characters/miku_animated.fbx`

## 备选方案（若第三步关口失败）

若 CS2 模型无法导出可用动画，改用 **Mixamo 动画库**：

1. 访问 https://www.mixamo.com（Adobe 账号，免费）
2. 下载 CS 风格动作：run / walk / crouch / jump / death / idle
3. 下载时选择 **Without Skin**（只要动画数据）
4. Blender 中直接导入 Mixamo FBX，Mixamo 骨骼是标准 humanoid 命名，
   **改名映射到 cat 骨骼即可**，无需复杂重定向

Mixamo 方案的代价：动作不是 CS 原版手感（缺少 CS 特有的武器持握、瞄准层等），
但技术上更稳定，且避开了 CS 骨骼轴向的坑。

## 版权提醒

CS2 提取的资产、Mixamo 动画、以及 Miku 形象（版权归 Crypton Future Media），
**均仅限本地个人学习与原型验证，不可分发、不可商用**。
