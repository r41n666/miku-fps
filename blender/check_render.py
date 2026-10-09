"""
渲染结果量化检查
==================
用途：用「亮像素占比」客观判断渲染图里到底有没有东西，
     避免肉眼把深色背景误判成「模型丢了」。

为什么需要这个：
    深蓝灰背景 (0.04,0.05,0.06) 在低阈值下会被算作「非黑」，
    肉眼看深色图也难以区分「渲出了但很暗」和「什么都没渲」。
    ⇒ 必须用 bright_ratio 量化，阈值取 0.35（模型是浅色/白色，背景远低于此值）。

用法（必须在 Blender 里跑，因为要读 Blender 的图像 API）：
    blender -b --factory-startup --python check_render.py -- --dir <图片目录>

判读标准（实测校准）：
    bright_ratio > 0.02  → 有内容，渲成功了
    bright_ratio = 0.00  → 纯背景，模型完全没进画面

实测数据（cat_hatsune_miku.glb + 仿真 CS2 骨架）：
    正常渲出   0.08 ~ 0.16
    纯背景     0.00
"""

import bpy
import sys
import os
import json

THRESHOLD = 0.35      # 亮像素阈值
MIN_CONTENT = 0.02    # 判定「有内容」的 bright_ratio 下限


def main():
    argv = sys.argv
    if "--" not in argv:
        print("need --dir <path>")
        return
    args = argv[argv.index("--") + 1:]
    d = args[args.index("--dir") + 1] if "--dir" in args else None
    # ⚠️ 实测坑：无头模式下 Blender 以「当前盘根」解析相对路径，
    #    bpy.data.images.load 用相对路径会报 No such file ⇒ 必须转绝对。
    if d:
        d = os.path.abspath(d)
    if not d or not os.path.isdir(d):
        print("bad dir:", d)
        return

    results = {}
    for f in sorted(os.listdir(d)):
        if not f.lower().endswith(".png"):
            continue
        p = os.path.join(d, f)
        img = bpy.data.images.load(p)
        px = list(img.pixels)
        bright = sum(1 for i in range(0, len(px), 4)
                     if px[i] > THRESHOLD
                     or px[i + 1] > THRESHOLD
                     or px[i + 2] > THRESHOLD)
        total = len(px) // 4
        ratio = bright / total if total else 0.0
        results[f] = ratio
        flag = "OK " if ratio > MIN_CONTENT else "EMPTY"
        print("%-24s %s bright_ratio=%.5f (%d/%d)"
              % (f, flag, ratio, bright, total))
        bpy.data.images.remove(img)

    ok = [f for f, r in results.items() if r > MIN_CONTENT]
    bad = [f for f, r in results.items() if r <= MIN_CONTENT]
    print("\n###SUMMARY### has_content=%d empty=%d" % (len(ok), len(bad)))
    if bad:
        print("###EMPTY_FILES###", json.dumps(bad, ensure_ascii=False))
        print("###HINT### 方位角/相机参数不对，或模型不在视锥内。"
              "用 render_probe.py 扫 8 个方位角找正面。")


if __name__ == "__main__":
    main()