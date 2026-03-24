#!/usr/bin/env python3
"""
KHY的小工具 - 一键部署脚本
"""

import os
import sys
import subprocess
import platform
import urllib.request
import urllib.parse

GITEE  = "https://gitee.com/procedure-haoyuan/my-tools/raw/main"
GITHUB = "https://raw.githubusercontent.com/Program-master-leader/my-tools/main"

BOOTSTRAP = ["gui_center.py", "tools.json"]
DEPS = ["rich", "pystray", "Pillow", "tkinterdnd2", "pywin32"]

IS_WIN = platform.system() == "Windows"
INSTALL_DIR = os.path.dirname(os.path.abspath(__file__))

# 当前使用的 Python 版本，新机也安装同一版本
PY_VERSION  = "3.14.3"
PY_INSTALLER_URL = (
    "https://www.python.org/ftp/python/3.14.3/python-3.14.3-amd64.exe"
)
# Gitee 镜像（国内备用，如有）
PY_INSTALLER_URL_CN = (
    "https://mirrors.huaweicloud.com/python/3.14.3/python-3.14.3-amd64.exe"
)


def log(msg, ok=True):
    print(f"  {'✓' if ok else '✗'} {msg}")


def find_python():
    """在常见位置查找 python 可执行文件，返回路径或 None"""
    candidates = ["python", "python3", "py"]
    for c in candidates:
        try:
            r = subprocess.run([c, "--version"], capture_output=True, timeout=5)
            if r.returncode == 0:
                return c
        except Exception:
            pass
    # 扫描常见安装目录
    for base in [
        os.path.expanduser("~\\AppData\\Local\\Programs\\Python"),
        "C:\\Python3",
        "D:\\Python3",
    ]:
        if not os.path.isdir(base):
            continue
        for sub in sorted(os.listdir(base), reverse=True):
            exe = os.path.join(base, sub, "python.exe")
            if os.path.exists(exe):
                return exe
    return None


def install_python():
    """下载并静默安装 Python，安装到用户目录（不需要管理员）"""
    print(f"\n未检测到 Python，正在下载 Python {PY_VERSION}...")
    tmp = os.path.join(os.environ.get("TEMP", INSTALL_DIR), f"python-{PY_VERSION}-amd64.exe")

    downloaded = False
    for url, label in [(PY_INSTALLER_URL_CN, "华为云镜像"), (PY_INSTALLER_URL, "Python官网")]:
        try:
            print(f"  尝试从 {label} 下载...", end="", flush=True)

            def progress(count, block, total):
                if total > 0:
                    pct = min(count * block * 100 // total, 100)
                    print(f"\r  尝试从 {label} 下载... {pct}%", end="", flush=True)

            urllib.request.urlretrieve(url, tmp, reporthook=progress)
            print()
            log(f"下载完成（{label}）")
            downloaded = True
            break
        except Exception as e:
            print()
            log(f"{label} 下载失败: {e}", ok=False)

    if not downloaded:
        print("\n✗ Python 下载失败，请手动安装后重试：")
        print(f"  {PY_INSTALLER_URL}")
        input("按回车退出...")
        sys.exit(1)

    print(f"  正在安装 Python {PY_VERSION}（静默安装，请稍候）...")
    # /quiet 静默, PrependPath=1 自动加PATH, Include_pip=1 含pip
    r = subprocess.run(
        [tmp, "/quiet", "InstallAllUsers=0", "PrependPath=1",
         "Include_pip=1", "Include_launcher=1"],
        timeout=300)
    if r.returncode != 0:
        log(f"安装失败，返回码: {r.returncode}", ok=False)
        print("  请手动双击安装包：", tmp)
        input("按回车退出...")
        sys.exit(1)

    log(f"Python {PY_VERSION} 安装完成")
    # 刷新当前进程 PATH
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment")
        new_path = winreg.QueryValueEx(key, "PATH")[0]
        os.environ["PATH"] = new_path + ";" + os.environ.get("PATH", "")
    except Exception:
        pass
    return find_python()


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


def install_deps(python_exe):
    print("\n安装基础依赖...")
    for dep in DEPS:
        r = subprocess.run(
            f'"{python_exe}" -m pip install {dep} -q --disable-pip-version-check',
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
        except Exception:
            current = ""
        if INSTALL_DIR.lower() not in current.lower():
            winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ,
                              current + ";" + INSTALL_DIR)
        winreg.CloseKey(key)
        log("已添加到 PATH，重开终端后输入 '中心' 可用")
    except Exception as e:
        log(f"PATH 注册失败: {e}", ok=False)


def create_shortcut(python_exe):
    if not IS_WIN:
        return
    print("\n创建桌面快捷方式...")
    try:
        pythonw = os.path.join(os.path.dirname(python_exe), "pythonw.exe")
        if not os.path.exists(pythonw):
            pythonw = python_exe
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        lnk     = os.path.join(desktop, "应用管理中心.lnk")
        script  = os.path.join(INSTALL_DIR, "gui_center.py")
        ps = (
            f'$ws=New-Object -ComObject WScript.Shell;'
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


def launch(python_exe):
    script  = os.path.join(INSTALL_DIR, "gui_center.py")
    pythonw = os.path.join(os.path.dirname(python_exe), "pythonw.exe")
    if IS_WIN and os.path.exists(pythonw):
        subprocess.Popen(f'"{pythonw}" "{script}"', shell=True)
    else:
        subprocess.Popen([python_exe, script])


def main():
    if IS_WIN:
        subprocess.run("chcp 65001 >nul 2>&1", shell=True)

    print("=" * 50)
    print("  KHY的小工具 - 一键部署")
    print(f"  目录: {INSTALL_DIR}")
    print("=" * 50)

    # ── 检测 / 安装 Python ──
    python_exe = find_python()
    if python_exe:
        r = subprocess.run([python_exe, "--version"], capture_output=True, text=True)
        log(f"已检测到 {r.stdout.strip() or r.stderr.strip()}")
    else:
        if not IS_WIN:
            print("✗ 未检测到 Python，请手动安装后重试")
            input("按回车退出...")
            sys.exit(1)
        python_exe = install_python()
        if not python_exe:
            print("✗ Python 安装后仍无法找到，请重启后再运行")
            input("按回车退出...")
            sys.exit(1)

    # ── 下载核心文件 ──
    print("\n下载启动文件...")
    ok = all(download_file(f) for f in BOOTSTRAP)
    if not ok:
        print("\n✗ 核心文件下载失败，请检查网络后重试")
        input("按回车退出...")
        sys.exit(1)

    install_deps(python_exe)
    register_path()
    create_shortcut(python_exe)

    print("\n" + "=" * 50)
    print("  部署完成，正在启动...")
    print("  其余工具在「工具管理」页面按需下载")
    print("=" * 50)

    launch(python_exe)
    input("\n按回车关闭此窗口...")


if __name__ == "__main__":
    main()
