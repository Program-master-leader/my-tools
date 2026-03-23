#!/usr/bin/env python3
"""桌面整理工具 - 系统托盘常驻"""

import os
import sys
import shutil
import threading
import winreg
from PIL import Image, ImageDraw
import pystray

STARTUP_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "桌面整理工具"


def is_startup_enabled():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False


def set_startup(enable):
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0, winreg.KEY_SET_VALUE)
    if enable:
        # 用 pythonw.exe 避免弹出黑色命令行窗口
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        script = os.path.abspath(__file__)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{pythonw}" "{script}"')
    else:
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass
    winreg.CloseKey(key)

DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")

# 文件类型分类
CATEGORIES = {
    "图片": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico"},
    "文档": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".md"},
    "视频": {".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv"},
    "音乐": {".mp3", ".wav", ".flac", ".aac", ".ogg"},
    "压缩包": {".zip", ".rar", ".7z", ".tar", ".gz"},
    "程序": {".exe", ".msi", ".bat", ".cmd", ".ps1"},
    "代码": {".py", ".js", ".ts", ".html", ".css", ".java", ".cpp", ".c", ".json"},
}


def get_category(ext):
    ext = ext.lower()
    for category, exts in CATEGORIES.items():
        if ext in exts:
            return category
    return "其他"


def organize():
    moved = 0
    for filename in os.listdir(DESKTOP):
        src = os.path.join(DESKTOP, filename)
        # 跳过文件夹和快捷方式
        if os.path.isdir(src) or filename.endswith(".lnk"):
            continue
        ext = os.path.splitext(filename)[1]
        if not ext:
            continue
        category = get_category(ext)
        dst_dir = os.path.join(DESKTOP, category)
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, filename)
        # 避免覆盖同名文件
        if os.path.exists(dst):
            base, ext_ = os.path.splitext(filename)
            dst = os.path.join(dst_dir, f"{base}_1{ext_}")
        shutil.move(src, dst)
        moved += 1

    return moved


def create_icon():
    """生成一个简单的托盘图标"""
    img = Image.new("RGB", (64, 64), color=(52, 152, 219))
    draw = ImageDraw.Draw(img)
    # 画三条横线表示整理
    for y in [18, 30, 42]:
        draw.rectangle([12, y, 52, y + 6], fill="white")
    return img


def on_organize(icon, item):
    def run():
        moved = organize()
        icon.notify(f"整理完成，共移动 {moved} 个文件", "桌面整理")
    threading.Thread(target=run, daemon=True).start()


def on_toggle_startup(icon, item):
    enable = not is_startup_enabled()
    set_startup(enable)
    status = "已开启" if enable else "已关闭"
    icon.notify(f"开机自启 {status}", "桌面整理")
    # 刷新菜单
    icon.menu = build_menu(icon)


def on_quit(icon, item):
    icon.stop()


def build_menu(icon=None):
    startup_label = lambda item: "✓ 开机自启" if is_startup_enabled() else "  开机自启"
    return pystray.Menu(
        pystray.MenuItem("整理桌面", on_organize),
        pystray.MenuItem(startup_label, on_toggle_startup),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", on_quit),
    )


def main():
    icon = pystray.Icon(
        name="桌面整理",
        icon=create_icon(),
        title="桌面整理",
        menu=build_menu()
    )
    icon.run()


if __name__ == "__main__":
    main()
