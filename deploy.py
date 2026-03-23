#!/usr/bin/env python3
"""一键部署脚本 - 新电脑运行此脚本还原所有工具"""

import os
import sys
import subprocess
import platform

GITHUB = "https://github.com/Program-master-leader/my-tools.git"
GITEE  = "https://gitee.com/procedure-haoyuan/my-tools.git"
INSTALL_DIR = os.path.join(os.path.expanduser("~"), "my-tools")

IS_WIN = platform.system() == "Windows"

def run(cmd, **kwargs):
    print(f"  > {cmd}")
    return subprocess.run(cmd, shell=True, **kwargs)

def step(msg):
    print(f"\n{'='*50}\n  {msg}\n{'='*50}")

def install_deps():
    step("安装 Python 依赖")
    deps = ["pypdf", "python-docx", "docx2pdf", "rich", "pystray", "Pillow", "ollama"]
    for dep in deps:
        run(f'pip install {dep} -q')
    print("  ✓ 依赖安装完成")

def clone_repo():
    step("下载工具脚本")
    if os.path.exists(INSTALL_DIR):
        print(f"  目录已存在，更新代码...")
        run(f'git -C "{INSTALL_DIR}" pull')
    else:
        print(f"  从 Gitee 下载（国内优先）...")
        result = run(f'git clone {GITEE} "{INSTALL_DIR}"')
        if result.returncode != 0:
            print(f"  Gitee 失败，尝试 GitHub...")
            run(f'git clone {GITHUB} "{INSTALL_DIR}"')
    print(f"  ✓ 脚本已下载到 {INSTALL_DIR}")

def register_path():
    step("注册 '中心' 命令")
    if IS_WIN:
        bat = os.path.join(INSTALL_DIR, "中心.bat")
        if os.path.exists(bat):
            import winreg
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE)
                current = ""
                try:
                    current = winreg.QueryValueEx(key, "PATH")[0]
                except:
                    pass
                if INSTALL_DIR not in current:
                    winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, current + ";" + INSTALL_DIR)
                winreg.CloseKey(key)
                print("  ✓ 已添加到 PATH，重开终端后输入 '中心' 即可使用")
            except Exception as e:
                print(f"  ✗ PATH 注册失败: {e}")
        else:
            print("  ✗ 未找到 中心.bat")
    else:
        shell_rc = os.path.expanduser("~/.bashrc")
        if "zsh" in os.environ.get("SHELL", ""):
            shell_rc = os.path.expanduser("~/.zshrc")
        with open(shell_rc, "a") as f:
            f.write(f'\nexport PATH="$PATH:{INSTALL_DIR}"\n')
        print(f"  ✓ 已添加到 {shell_rc}，运行 source {shell_rc} 生效")

def register_context_menu():
    step("注册右键菜单")
    if IS_WIN:
        reg_script = os.path.join(INSTALL_DIR, "register_menu.py")
        if os.path.exists(reg_script):
            run(f'python "{reg_script}"')
        else:
            print("  ✗ 未找到 register_menu.py")
    else:
        print("  右键菜单仅支持 Windows，跳过")

def create_dirs():
    step("创建必要目录")
    ideas = os.path.join(INSTALL_DIR, "ideas")
    os.makedirs(ideas, exist_ok=True)
    print(f"  ✓ ideas 目录: {ideas}")

def main():
    print("\n" + "="*50)
    print("  应用管理中心 - 一键部署")
    print("  系统:", platform.system(), platform.release())
    print("="*50)

    # 检查 git
    if subprocess.run("git --version", shell=True, capture_output=True).returncode != 0:
        print("\n✗ 未检测到 Git，请先安装 Git：https://git-scm.com")
        input("按回车退出...")
        sys.exit(1)

    clone_repo()
    install_deps()
    create_dirs()
    register_path()

    if IS_WIN:
        ans = input("\n是否注册右键「查看文件说明」菜单？需要管理员权限 (y/n): ").strip().lower()
        if ans == "y":
            register_context_menu()

    print("\n" + "="*50)
    print("  ✓ 部署完成！")
    print(f"  工具目录: {INSTALL_DIR}")
    print("  重新打开终端，输入 '中心' 开始使用")
    print("="*50)
    input("\n按回车关闭...")

if __name__ == "__main__":
    main()
