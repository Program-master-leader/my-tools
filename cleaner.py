#!/usr/bin/env python3
"""电脑清理工具 - 系统托盘常驻"""

import os
import sys
import shutil
import hashlib
import threading
import winreg
from PIL import Image, ImageDraw
import pystray

STARTUP_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "电脑清理工具"

TEMP_DIRS = [
    os.environ.get("TEMP", ""),
    os.environ.get("TMP", ""),
    os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Temp"),
]

TEMP_EXTS = {".tmp", ".log", ".bak", ".old", ".chk", ".gid", ".dmp"}
INCOMPLETE_EXTS = {".crdownload", ".part", ".partial", ".download", ".!ut"}

# 扫描重复文件的目录
SCAN_DIRS = [
    os.path.join(os.path.expanduser("~"), "Downloads"),
    os.path.join(os.path.expanduser("~"), "Desktop"),
    os.path.join(os.path.expanduser("~"), "Documents"),
]


# ── 清理逻辑 ──────────────────────────────────────────

def clean_temp():
    count, size = 0, 0
    for d in TEMP_DIRS:
        if not d or not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            path = os.path.join(d, name)
            try:
                if os.path.isfile(path) and os.path.splitext(name)[1].lower() in TEMP_EXTS:
                    size += os.path.getsize(path)
                    os.remove(path)
                    count += 1
                elif os.path.isdir(path):
                    size += get_dir_size(path)
                    shutil.rmtree(path, ignore_errors=True)
                    count += 1
            except Exception:
                pass
    return count, size


def clean_incomplete():
    count, size = 0, 0
    dl_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    if not os.path.isdir(dl_dir):
        return count, size
    for name in os.listdir(dl_dir):
        path = os.path.join(dl_dir, name)
        if os.path.isfile(path) and os.path.splitext(name)[1].lower() in INCOMPLETE_EXTS:
            try:
                size += os.path.getsize(path)
                os.remove(path)
                count += 1
            except Exception:
                pass
    return count, size


def clean_empty_folders():
    count = 0
    for base in SCAN_DIRS:
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base, topdown=False):
            if root == base:
                continue
            try:
                if not os.listdir(root):
                    os.rmdir(root)
                    count += 1
            except Exception:
                pass
    return count


def file_hash(path, chunk=8192):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk_ := f.read(chunk):
            h.update(chunk_)
    return h.hexdigest()


def clean_duplicates():
    seen, count, size = {}, 0, 0
    for base in SCAN_DIRS:
        if not os.path.isdir(base):
            continue
        for root, _, files in os.walk(base):
            for name in files:
                path = os.path.join(root, name)
                try:
                    key = (os.path.getsize(path), file_hash(path))
                    if key in seen:
                        size += os.path.getsize(path)
                        os.remove(path)
                        count += 1
                    else:
                        seen[key] = path
                except Exception:
                    pass
    return count, size


def get_dir_size(path):
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except Exception:
                pass
    return total


def fmt_size(b):
    for unit in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} GB"


# ── 托盘 ─────────────────────────────────────────────

def run_clean(icon):
    def task():
        icon.notify("正在清理，请稍候...", "电脑清理")
        lines = []

        c, s = clean_temp()
        lines.append(f"临时文件: {c} 个 ({fmt_size(s)})")

        c, s = clean_incomplete()
        lines.append(f"未完成下载: {c} 个 ({fmt_size(s)})")

        c = clean_empty_folders()
        lines.append(f"空文件夹: {c} 个")

        c, s = clean_duplicates()
        lines.append(f"重复文件: {c} 个 ({fmt_size(s)})")

        icon.notify("\n".join(lines), "清理完成")

    threading.Thread(target=task, daemon=True).start()


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
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        script = os.path.abspath(__file__)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{pythonw}" "{script}"')
    else:
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass
    winreg.CloseKey(key)


def on_toggle_startup(icon, item):
    set_startup(not is_startup_enabled())
    status = "已开启" if is_startup_enabled() else "已关闭"
    icon.notify(f"开机自启 {status}", "电脑清理")


def create_icon():
    img = Image.new("RGB", (64, 64), color=(231, 76, 60))
    draw = ImageDraw.Draw(img)
    draw.ellipse([10, 10, 54, 54], outline="white", width=5)
    draw.line([32, 20, 32, 44], fill="white", width=5)
    draw.line([22, 44, 42, 44], fill="white", width=5)
    return img


def build_menu():
    startup_label = lambda item: "✓ 开机自启" if is_startup_enabled() else "  开机自启"
    return pystray.Menu(
        pystray.MenuItem("立即清理", lambda icon, item: run_clean(icon)),
        pystray.MenuItem(startup_label, on_toggle_startup),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", lambda icon, item: icon.stop()),
    )


def main():
    icon = pystray.Icon(
        name="电脑清理",
        icon=create_icon(),
        title="电脑清理工具",
        menu=build_menu()
    )
    icon.run()


if __name__ == "__main__":
    main()
