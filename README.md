# miku-fps

类 Counter-Strike 的 FPS 原型 · T/CT 阵营使用 Miku 猫耳角色模型

## 状态

**阶段：动画资产管线完成（重定向 → 烘焙 → Godot 导入验证 PASS）—— 下一步 Godot 工程搭建**

- ✅ 可行性确认：无 VAC 风险，无需下载 CS:GO（详见 `docs/preflight_report.md`）
- ✅ 真实干员 `ctm_sas` 端到端跑通（2026-10-09）：MAPPED 21 / MISSING 0，6 动作渲染验证
- ✅ **烘焙 + Godot 4.7.2 导入验证通过**（2026-10-11）：`miku_anim6.glb`
  （6 动画 / 111 骨 / 动画驱动骨骼实测 201° / 交付格式判定为 GLB）
  —— 详见 `docs/validation_report.md` 第十节
- 🔄 下一步：Godot 工程搭建（接入角色 + 武器 + 音效，做可玩射击原型）

**换设备接手 → 读 `HANDOFF.md`**（环境清单 / CLI 导出步骤 / 已验证命令 / 踩坑速查）。

## 技术路线

| 维度 | 选型 |
|---|---|
| 引擎 | Godot 4.7.2（`~/Desktop/Godot_v4.7.2-stable_win64_console.exe`） |
| 角色模型 | `cat_hatsune_miku.glb`（111 骨骼，T/CT 共用，靠配色区分） |
| 动画来源 | CS2 原版动画，经 Source 2 Viewer 导出后重定向 |
| 音频 | `hit_female/` 27 个受击音效（44.1kHz/16bit/立体声，Godot 原生支持） |
| 武器 | ak-47 / usp-s / butterfly knife（已有 glb） |
| 素材来源 | CS2 VPK 离线提取（`pak01_dir.vpk` + `pak01_000..039.vpk`） |

## 目录结构

```
miku-fps/
├── docs/
│   ├── preflight_report.md    资产核查报告（实测数据）
│   ├── bone_mapping.md        骨骼映射表（23 根核心骨）
│   └── next_steps.md          下一步操作指南
├── blender/
│   └── retarget_cs2_to_miku.py   骨骼重定向脚本（Blender 内运行）
├── tools/
│   └── setup_blender.bat      工具链安装脚本
├── assets/
│   ├── characters/            角色模型
│   ├── weapons/               武器模型
│   └── audio/                 受击音效 ×27
└── prototype/                 验证产物（CS2 导出模型等）
```

## 立即行动

```bash
# 1. 安装 Blender（本地 MSI，无需联网）
#    右键 tools/setup_blender.bat 以管理员身份运行

# 2. 详细步骤见 docs/next_steps.md
```

## 合规边界

- ✅ 离线提取本机 CS2 安装目录中的资产，用于个人学习
- ❌ 不修改 Steam 游戏文件
- ❌ 不做任何 CS2 客户端进程注入（VAC 红线）
- ❌ 不分发、不商用（CS2 资产归 Valve；Miku 形象归 Crypton Future Media）
