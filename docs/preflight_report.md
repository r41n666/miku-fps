# Pre-flight 核查报告 · 资产可行性

> 执行时间：2026-10-07
> 方法：直接解析资产二进制 + 扫描 CS2 VPK 索引 + 交叉验证社区骨骼索引表
> 结论：**项目可行。已消除 T-pose 阻塞。**

## 一、角色模型核查

| 文件 | 大小 | 来源 | 骨骼 | 动画 | 判定 |
|---|---|---|---|---|---|
| `cat_hatsune_miku.glb` | 3.72 MB | Sketchfab-0.5.0 | **111 根** | 2（`ArmatureAction` 2.5s / `idle` 0.083s） | ✅ **采用** |
| `miku.glb` | 4.46 MB | Sketchfab-12.68.0 | **0 根** | **0 个** | ❌ 已备份，不使用 |

### 关键修正记录
初次用正则按 `upperarm`/`knee` 分类时，因模型用的是 `upper_arm` / `lower_leg`（下划线分词），
误判为"缺少手臂与膝盖骨"。导出全量 111 骨后确认**骨架完整人形**：

```
hips_106 → spine_95 → chest_94 → neck_50 → head_49
                              ├─ shoulder.L_69 → upper_arm.L_68 → lower_arm.L_67 → hand.L_66
                              └─ shoulder.R_88 → upper_arm.R_87 → lower_arm.R_86 → hand.R_85
 hips_106 → upper_leg.L_100 → lower_leg.L_99 → foot.L_97 → toes.L_96
          → upper_leg.R_105 → lower_leg.R_104 → foot.R_102 → toes.R_101
```
另有 24 根手指骨（可不用）、18 根 ponytail、6 根猫耳、6 根嘴部、26 根 `Bone.*` 装饰骨。

**用户决策：T 与 CT 两侧均使用 `cat_hatsune_miku.glb`**，通过不同配色/附件区分阵营。
这消除了 T-pose 阻塞——111 根骨骼足够承载 CS2 动画重定向。

## 二、CS2 资产核查

安装路径：`D:\Program Files\steam\steamapps\common\Counter-Strike Global Offensive\`
引擎：Source 2，全量安装（`pak01_dir.vpk` 7.7MB 索引 + `pak01_000..039.vpk`）

扫描 `pak01_dir.vpk` 索引（146,509 个可读路径串）确认：

| 资源类型 | 数量/示例 | 用途 |
|---|---|---|
| 干员模型 | **74 个** `agents/models/ctm_sas`, `ctm_fbi`, `ctm_st6`, `ctm_swat`, `ctm_gendarmerie`, `ctm_diver`… | 动画源 + 可选角色 |
| 原版受击音 | `sounds/physics/flesh/flesh_impact_bullet1..4` | 可与 hit_female 混用 |
| 地图模型 | `models/cs_italy/*`（建筑/门/箱/窗帘） | 场景搭建 |
| 武器模型 | `models/` 下大量 | 武器 |

**不需要下载 CS:GO。** 提取工具用 Source 2 Viewer（github.com/ValveResourceFormat，活跃维护中），
可直接把 `.vmdl_c` 导出为 glTF/GLB，自带骨骼 + 动画导出，附 CLI 批量模式。

## 三、音频核查

`hit_female/` 共 **27 个 wav**，总计 4.94 MB。
格式**完全统一**：44,100 Hz / 16-bit / 立体声 / PCM。
Godot 4 原生支持，**零转换成本**，可直接投入引擎使用。

编号不连续（01,03,05,06,08,09,10,12,13,17,18,22,23,25,26,27,28,29,31,32,34,35,36,37,38,39,40），
说明原曲库本身抽稀过；Godot 导入时按文件名建立随机池即可。

## 四、武器与附件（顺带发现，均已入库）

| 文件 | 大小 | 用途 |
|---|---|---|
| `ak-47.glb` | 4.86 MB | 主武器 |
| `usp-s__cyrex.glb` | 0.94 MB | 手枪 |
| `fps_butterfly_knife.glb` | 4.62 MB | 近战 |

## 五、VAC 与合规边界

**VAC 风险 = 零**，前提是严守以下红线：

- ✅ 可以：离线读取安装目录 VPK → 导出资产 → 导入自建引擎（Godot）
- ✅ 可以：使用 Steam 创意工坊地图（官方支持）
- ❌ 不要：任何向 CS2 客户端进程注入代码/修改内存的操作
- ❌ 不要：使用第三方客户端皮肤替换器 / 外部 overlay 注入类工具

补充澄清：社区常提的 CounterStrikeSharp / MetaMod:Source 是**服务器端**插件框架，
不修改客户端，对账号安全无害，但**无法用于本项目**（不能自定义模型、不能做单机 FPS）。

**版权边界**：CS2 资产与音频仅限本地个人学习/原型用途，不可分发、不可商用。
Miku 角色形象版权归 Crypton Future Media 所有，同样仅限非商业用途。

## 六、工具链现状

| 工具 | 状态 | 路径/说明 |
|---|---|---|
| Godot 4.7.2 | ✅ 已装 | `C:\Users\Administrator\Desktop\Godot_v4.7.2-stable_win64_console.exe` |
| .NET | ✅ 已装 | `C:\Program Files\dotnet\dotnet.exe`（Source 2 Viewer 依赖） |
| Blender | ❌ 未装 | 安装包在 `Downloads\blender-5.2.2-windows-x64.msi`，未执行安装 |
| Source 2 Viewer | ❌ 未装 | 需从 GitHub Releases 下载 |

## 七、遗留风险

1. **CS2 干员模型实际骨骼命名未实测** — 映射表基于社区索引文档交叉验证，需导出后确认
2. **cat 模型 rest pose 是否标准 T-pose** — 若不是需先做 rest pose 校正，否则重定向会错位
3. **MMD 骨骼局部轴向与 CS2 差异** — 重定向最易踩坑处，可能需逐轴旋转补偿
4. **ponytail / 猫耳骨骼权重** — 需检查重定向后是否被拉伸
5. **cat 模型仅 2 个动作** — 项目需要 run/walk/crouch/jump/death 共 5+ 个，全部依赖 CS2 动画重定向产出

## 八、下一步（go/no-go 关口）

**先做资产验证 prototype**，按此顺序：

1. 安装 Blender + Source 2 Viewer
2. 用 S2V 导出一个 CT 干员模型（如 `ctm_sas`）到 glTF，**确认动画能正常播放**
3. Blender 中按 `docs/bone_mapping.md` 建立骨骼约束，把 CS 动画重定向到 cat 骨骼
4. 验证 5 个核心动作：run / walk / crouch / jump / death
5. 导出 FBX → 导入 Godot 4.7.2，在引擎里播放验证

**第 2 步是 go/no-go 关口**：若 S2V 导出的模型无法正常播放动画，需立即切换到备选方案
（Mixamo 动画库直接套 cat 骨骼，不需重定向）。
