#!/usr/bin/env python3
"""桌面图片按主色调重命名，使同色调图片聚集在一起"""

import os
from PIL import Image

DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")

COLOR_RANGES = [
    ("1红", [(0, 15), (345, 360)]),
    ("2橙", [(15, 45)]),
    ("3黄", [(45, 75)]),
    ("4绿", [(75, 150)]),
    ("5青", [(150, 195)]),
    ("6蓝", [(195, 255)]),
    ("7紫", [(255, 345)]),
]

SUPPORTED = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# 用于识别已加过前缀的文件，避免重复处理
PREFIX_MARKS = [name for name, _ in COLOR_RANGES] + ["0灰"]


def get_dominant_color(image_path):
    img = Image.open(image_path).convert("RGB")
    img = img.resize((100, 100))

    color_count = {}
    for r, g, b in img.getdata():
        r_, g_, b_ = r / 255, g / 255, b / 255
        cmax, cmin = max(r_, g_, b_), min(r_, g_, b_)
        delta = cmax - cmin
        s = delta / cmax if cmax != 0 else 0

        if s < 0.2 or cmax < 0.2:
            label = "0灰"
        else:
            if delta == 0:
                h = 0
            elif cmax == r_:
                h = 60 * (((g_ - b_) / delta) % 6)
            elif cmax == g_:
                h = 60 * (((b_ - r_) / delta) + 2)
            else:
                h = 60 * (((r_ - g_) / delta) + 4)

            label = "其他"
            for name, ranges in COLOR_RANGES:
                for lo, hi in ranges:
                    if lo <= h < hi:
                        label = name
                        break
                if label != "其他":
                    break

        color_count[label] = color_count.get(label, 0) + 1

    return max(color_count, key=color_count.get)


def already_prefixed(filename):
    """检查文件名是否已有色调前缀"""
    for mark in PREFIX_MARKS:
        if filename.startswith(f"[{mark}]"):
            return True
    return False


def sort_desktop_images():
    print(f"扫描桌面: {DESKTOP}\n")

    images = [
        f for f in os.listdir(DESKTOP)
        if os.path.splitext(f)[1].lower() in SUPPORTED
        and os.path.isfile(os.path.join(DESKTOP, f))
        and not already_prefixed(f)
    ]

    if not images:
        print("没有找到需要处理的图片")
        return

    print(f"找到 {len(images)} 张图片，开始分析...\n")

    for filename in images:
        src = os.path.join(DESKTOP, filename)
        try:
            color = get_dominant_color(src)
            new_name = f"[{color}]{filename}"
            dst = os.path.join(DESKTOP, new_name)
            os.rename(src, dst)
            print(f"  [{color}] {filename}")
        except Exception as e:
            print(f"  [失败] {filename}: {e}")

    print("\n✓ 完成，请将桌面设置为「按名称排序」，同色调图片会自动聚在一起")
    print("  右键桌面 -> 排序方式 -> 名称")


def undo_rename():
    """还原所有前缀重命名"""
    print("还原文件名...\n")
    for filename in os.listdir(DESKTOP):
        for mark in PREFIX_MARKS:
            prefix = f"[{mark}]"
            if filename.startswith(prefix):
                new_name = filename[len(prefix):]
                os.rename(
                    os.path.join(DESKTOP, filename),
                    os.path.join(DESKTOP, new_name)
                )
                print(f"  还原: {filename} -> {new_name}")
                break
    print("\n✓ 还原完成")


if __name__ == "__main__":
    print("1. 按色调重命名（聚集同色调图片）")
    print("2. 还原所有文件名")
    choice = input("\n请选择: ").strip()
    if choice == "1":
        sort_desktop_images()
    elif choice == "2":
        undo_rename()
    else:
        print("无效选择")
    input("\n按回车关闭...")
