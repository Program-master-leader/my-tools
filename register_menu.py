#!/usr/bin/env python3
"""注册/卸载右键菜单 - 需要管理员权限"""

import os
import sys
import winreg
import ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def register(enable):
    python_exe = sys.executable.replace("python.exe", "pythonw.exe")
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "file_info.py")
    cmd = f'"{python_exe}" "{script}" "%1"'

    keys = [
        r"*\shell\查看文件说明",
        r"Directory\shell\查看文件说明",
        r"Directory\Background\shell\查看文件说明",
    ]

    for key_path in keys:
        if enable:
            try:
                key = winreg.CreateKeyEx(winreg.HKEY_CLASSES_ROOT, key_path, 0, winreg.KEY_WRITE)
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "查看文件说明 (AI)")
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, "shell32.dll,21")
                winreg.CloseKey(key)
                cmd_key = winreg.CreateKeyEx(winreg.HKEY_CLASSES_ROOT, key_path + r"\command", 0, winreg.KEY_WRITE)
                winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, cmd)
                winreg.CloseKey(cmd_key)
                print(f"✓ 注册: {key_path}")
            except Exception as e:
                print(f"✗ 失败: {key_path} -> {e}")
        else:
            for sub in [r"\command", ""]:
                try:
                    winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, key_path + sub)
                    print(f"✓ 删除: {key_path + sub}")
                except:
                    pass

if __name__ == "__main__":
    if not is_admin():
        print("需要管理员权限，正在请求提权...")
        # 自动以管理员身份重新运行
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{os.path.abspath(__file__)}"', None, 1
        )
        sys.exit()

    print("1. 注册右键菜单")
    print("2. 卸载右键菜单")
    choice = input("请选择: ").strip()
    if choice == "1":
        register(True)
        print("\n完成！右键任意文件或文件夹即可看到「查看文件说明」")
    elif choice == "2":
        register(False)
        print("\n已卸载")
    else:
        print("无效输入")
    input("\n按回车关闭...")
