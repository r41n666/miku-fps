# Godot 导入验证工具 · miku-fps

验证「烘焙导出的 miku_anim6.glb / .fbx」在 Godot 4.7.2 中的导入质量:
动画齐全 / 骨骼数 / rest 尺度与朝向 / 动画是否真实驱动骨骼。

## 用法

1. 把烘焙产物复制进本目录(与 project.godot 同级):
   `miku_anim6.glb`(必须)、`miku_anim6.fbx`(可选)
2. 导入 + 检查(两条命令):

```bash
GODOT="C:/Users/13569/Desktop/Godot_v4.7.2-stable_win64_console.exe"
"$GODOT" --headless --path "<本目录>" --import
"$GODOT" --headless --path "<本目录>" --script res://check_anims.gd
```

3. 看输出标记判读:

| 标记 | 含义 | 合格标准 |
|---|---|---|
| `###ANIMS###` | 动画列表 | 应恰好 6 个 `MKI_*` |
| `###SKELETON###` | 骨骼数 | 111 |
| `###BONE_REST###` | rest 骨骼位置 | 脚 Y≈0、头 Y≈1.24、手 ±0.55(T-pose、Y-up) |
| `###TRACK_SAMPLE###` | 轨道键值变化 | keys≈30 且 ang0->mid 明显非 0 |
| `###ANIM_DRIVEN###` | 动画驱动骨骼的旋转变化总和 | > 100°(实测 walk ≈ 201°) |

## 已知结论(2026-10-11 实测)

- **GLB:全项通过 —— 交付格式**(Godot 原生支持,尺度/朝向正确)
- **FBX:动画数据同样可用**,但 Godot 导入后 scale≈1/100、朝向为 Z-up
  → 备选格式,暂不推荐(如需修:导出侧调轴向 / 导入侧补 scale)
