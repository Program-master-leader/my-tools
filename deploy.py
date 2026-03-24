#!/usr/bin/env python3
"""
一键部署脚本 - 只下载启动器，其余按需下载
"""

import os
import sys
import subprocess
import platform
import urllib.request
import urllib.parse

GITEE  = "https://gitee.com/procedure-haoyuan/my-tools/raw/main"
GITHUB = "https://raw.githubusercontent.com/Program-master-leader/my-tools/main"

# 只下载启动必须的两个文件
BOOTSTRAP = ["gui_center.py", "tools.json"]

DEPS = ["rich", "pystray", "Pillow"]

IS_WIN = platform.system() == "Windows"
INSTALL_DIR = os.path.dirname(os.path.abspath(__file__))


def log(msg, ok=True):
    print(f"  {'✓' if ok else '✗'} {msg}")


def download_file(filename):
    dst = os.path.join(INSTALL_DIR, filename)
    for base, label in [(GITEE, "Gitee"), (GITHUB, "GitHub")]:
        try:
            urllib.request.urlretrieve(f"{base}/{urllib.parse.quote(filename)}", dst)
            log(f"{filename}（来自 {label}）")
            return True
        except Exception:
            continue
    log(f"{filename} 下载失败", ok=False)
    return False


def install_deps():
    print("\n安装基础依赖...")
    for dep in DEPS:
        r = subprocess.run(f'pip install {dep} -q --disable-pip-version-check',
                           shell=True, capture_output=True)
        log(dep, r.returncode == 0)


def register_path():
    if not IS_WIN:
        return
    print("\n注册 '中心' 命令...")
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment",
                             0, winreg.KEY_SET_VALUE | winreg.KEY_READ)
        try:
            current = winreg.QueryValueEx(key, "PATH")[0]
        except:
            current = ""
        if INSTALL_DIR.lower() not in current.lower():
            winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ,
                              current + ";" + INSTALL_DIR)
        winreg.CloseKey(key)
        log("已添加到 PATH，重开终端后输入 '中心' 可用")
    except Exception as e:
        log(f"PATH 注册失败: {e}", ok=False)


def create_shortcut():
    if not IS_WIN:
        return
    print("\n创建桌面快捷方式...")
    try:
        desktop  = os.path.join(os.path.expanduser("~"), "Desktop")
        lnk      = os.path.join(desktop, "应用管理中心.lnk")
        pythonw  = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        script   = os.path.join(INSTALL_DIR, "gui_center.py")
        ps = (
            f'$ws=$([Runtime.InteropServices.Marshal]::GetActiveObject("WScript.Shell") 2>$null);'
            f'if(!$ws){{$ws=New-Object -ComObject WScript.Shell}};'
            f'$sc=$ws.CreateShortcut("{lnk}");'
            f'$sc.TargetPath="{pythonw}";'
            f'$sc.Arguments=\'"{script}"\';'
            f'$sc.WorkingDirectory="{INSTALL_DIR}";'
            f'$sc.IconLocation="shell32.dll,21";'
            f'$sc.Save()'
        )
        subprocess.run(['powershell', '-Command', ps], capture_output=True)
        log("桌面快捷方式已创建")
    except Exception as e:
        log(f"快捷方式创建失败: {e}", ok=False)


def launch():
    script = os.path.join(INSTALL_DIR, "gui_center.py")
    if IS_WIN:
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        subprocess.Popen(f'"{pythonw}" "{script}"', shell=True)
    else:
        subprocess.Popen([sys.executable, script])


def main():
    if IS_WIN:
        subprocess.run("chcp 65001 >nul 2>&1", shell=True)

    print("=" * 50)
    print("  应用管理中心 - 一键部署")
    print(f"  目录: {INSTALL_DIR}")
    print("=" * 50)

    if sys.version_info < (3, 8):
        print("✗ 需要 Python 3.8+")
        input("按回车退出...")
        sys.exit(1)

    print("\n下载启动文件...")
    ok = all(download_file(f) for f in BOOTSTRAP)
    if not ok:
        print("\n✗ 核心文件下载失败，请检查网络后重试")
        input("按回车退出...")
        sys.exit(1)

    install_deps()
    register_path()
    create_shortcut()

    print("\n" + "=" * 50)
    print("  部署完成，正在启动...")
    print("  其余工具在「工具管理」页面按需下载")
    print("=" * 50)

    launch()
    input("\n按回车关闭此窗口...")


if __name__ == "__main__":
    main()
