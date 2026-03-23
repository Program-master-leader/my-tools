#!/usr/bin/env python3
"""应用管理中心"""

import os
import sys
import subprocess
import winreg
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

console = Console()

def clear():
    os.system("cls")

def pause():
    console.input("\n[dim]按回车继续...[/dim]")

def header(text):
    clear()
    console.print(Panel(f"[bold cyan]{text}[/bold cyan]", box=box.DOUBLE_EDGE, expand=False))
    console.print()

def success(msg): console.print(f"[bold green]✓[/bold green] {msg}")
def error(msg):   console.print(f"[bold red]✗[/bold red] {msg}")
def info(msg):    console.print(f"[bold yellow]→[/bold yellow] {msg}")

# ── 应用管理 ──────────────────────────────────────────

def list_installed_apps():
    apps = []
    keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    for hive, path in keys:
        try:
            key = winreg.OpenKey(hive, path)
            for i in range(winreg.QueryInfoKey(key)[0]):
                try:
                    sub = winreg.OpenKey(key, winreg.EnumKey(key, i))
                    name = winreg.QueryValueEx(sub, "DisplayName")[0]
                    try:
                        uninst = winreg.QueryValueEx(sub, "UninstallString")[0]
                    except:
                        uninst = ""
                    try:
                        ver = winreg.QueryValueEx(sub, "DisplayVersion")[0]
                    except:
                        ver = "-"
                    apps.append((name, ver, uninst))
                except:
                    pass
        except:
            pass
    return sorted(set(apps), key=lambda x: x[0].lower())

def app_manager():
    while True:
        header("📦 应用管理")
        console.print("  [cyan]1[/cyan]  查看已安装应用")
        console.print("  [cyan]2[/cyan]  卸载应用")
        console.print("  [cyan]3[/cyan]  打开应用文件夹")
        console.print("  [cyan]0[/cyan]  返回\n")
        choice = Prompt.ask("[bold]请选择[/bold]", choices=["0","1","2","3"], default="0")

        if choice == "0":
            break

        elif choice == "1":
            header("📦 已安装应用")
            with Progress(SpinnerColumn(), TextColumn("正在读取..."), transient=True) as p:
                p.add_task("", total=None)
                apps = list_installed_apps()
            table = Table(box=box.SIMPLE_HEAVY, show_lines=False)
            table.add_column("#", style="dim", width=5, justify="right")
            table.add_column("应用名称", style="white", min_width=30)
            table.add_column("版本", style="cyan", min_width=15)
            for i, (name, ver, _) in enumerate(apps, 1):
                table.add_row(str(i), name, ver)
            console.print(table)
            pause()

        elif choice == "2":
            header("🗑  卸载应用")
            with Progress(SpinnerColumn(), TextColumn("正在读取..."), transient=True) as p:
                p.add_task("", total=None)
                apps = list_installed_apps()
            table = Table(box=box.SIMPLE_HEAVY)
            table.add_column("#", style="dim", width=5, justify="right")
            table.add_column("应用名称", style="white", min_width=30)
            table.add_column("版本", style="cyan")
            for i, (name, ver, _) in enumerate(apps, 1):
                table.add_row(str(i), name, ver)
            console.print(table)
            try:
                idx = int(Prompt.ask("输入要卸载的序号（0取消）")) - 1
                if 0 <= idx < len(apps):
                    name, _, uninst = apps[idx]
                    if Confirm.ask(f"确认卸载 [bold red]{name}[/bold red]？"):
                        if uninst:
                            subprocess.Popen(uninst, shell=True)
                            success("已启动卸载程序")
                        else:
                            error("未找到卸载命令")
                    else:
                        info("已取消")
            except ValueError:
                error("无效输入")
            pause()

        elif choice == "3":
            subprocess.Popen("explorer shell:AppsFolder", shell=True)
            pause()

# ── 环境变量管理 ──────────────────────────────────────

def show_env_table(label, hive, path):
    header(f"🔧 {label}环境变量")
    try:
        key = winreg.OpenKey(hive, path)
        count = winreg.QueryInfoKey(key)[1]
        table = Table(box=box.SIMPLE_HEAVY, show_lines=True)
        table.add_column("变量名", style="cyan", min_width=20)
        table.add_column("值", style="white", min_width=40)
        for i in range(count):
            name, val, _ = winreg.EnumValue(key, i)
            table.add_row(name, val)
        console.print(table)
    except Exception as e:
        error(f"读取失败: {e}")

def env_manager():
    while True:
        header("🔧 环境变量管理")
        console.print("  [cyan]1[/cyan]  查看用户环境变量")
        console.print("  [cyan]2[/cyan]  查看系统环境变量")
        console.print("  [cyan]3[/cyan]  添加用户环境变量")
        console.print("  [cyan]4[/cyan]  删除用户环境变量")
        console.print("  [cyan]5[/cyan]  打开系统环境变量设置界面")
        console.print("  [cyan]0[/cyan]  返回\n")
        choice = Prompt.ask("[bold]请选择[/bold]", choices=["0","1","2","3","4","5"], default="0")

        if choice == "0":
            break

        elif choice == "1":
            show_env_table("用户", winreg.HKEY_CURRENT_USER, "Environment")
            pause()

        elif choice == "2":
            show_env_table("系统", winreg.HKEY_LOCAL_MACHINE,
                           r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")
            pause()

        elif choice == "3":
            header("➕ 添加环境变量")
            name = Prompt.ask("变量名")
            val  = Prompt.ask("变量值")
            if name:
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE)
                    winreg.SetValueEx(key, name, 0, winreg.REG_EXPAND_SZ, val)
                    winreg.CloseKey(key)
                    os.system(f'setx {name} "{val}" >nul')
                    success(f"已添加: {name} = {val}")
                except Exception as e:
                    error(f"失败: {e}")
            pause()

        elif choice == "4":
            header("➖ 删除环境变量")
            name = Prompt.ask("要删除的变量名")
            if name and Confirm.ask(f"确认删除 [bold red]{name}[/bold red]？"):
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE)
                    winreg.DeleteValue(key, name)
                    winreg.CloseKey(key)
                    success(f"已删除: {name}")
                except Exception as e:
                    error(f"失败: {e}")
            pause()

        elif choice == "5":
            subprocess.Popen("rundll32 sysdm.cpl,EditEnvironmentVariables", shell=True)
            pause()

# ── 文件管理 ──────────────────────────────────────────

def file_manager():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    while True:
        header("🗂  零散文件管理")
        console.print("  [cyan]1[/cyan]  整理桌面（按文件类型）")
        console.print("  [cyan]2[/cyan]  清理临时文件")
        console.print("  [cyan]3[/cyan]  清理未完成下载")
        console.print("  [cyan]4[/cyan]  清理空文件夹")
        console.print("  [cyan]5[/cyan]  合并 PDF")
        console.print("  [cyan]6[/cyan]  注册右键「查看文件说明」菜单")
        console.print("  [cyan]7[/cyan]  卸载右键菜单")
        console.print("  [cyan]0[/cyan]  返回\n")
        choice = Prompt.ask("[bold]请选择[/bold]", choices=["0","1","2","3","4","5","6","7"], default="0")

        if choice == "0":
            break

        elif choice == "1":
            script = os.path.join(script_dir, "desktop_organizer.py")
            if os.path.exists(script):
                subprocess.Popen(f'python "{script}"', shell=True)
                success("已启动桌面整理工具")
            else:
                error("未找到 desktop_organizer.py")
            pause()

        elif choice == "2":
            import tempfile, glob
            temp = tempfile.gettempdir()
            count = 0
            with Progress(SpinnerColumn(), TextColumn("清理中..."), transient=True) as p:
                p.add_task("", total=None)
                for f in glob.glob(os.path.join(temp, "*.tmp")) + glob.glob(os.path.join(temp, "*.log")):
                    try:
                        os.remove(f)
                        count += 1
                    except:
                        pass
            success(f"已清理 [bold]{count}[/bold] 个临时文件")
            pause()

        elif choice == "3":
            dl = os.path.join(os.path.expanduser("~"), "Downloads")
            count = 0
            for f in os.listdir(dl):
                if f.endswith((".crdownload", ".part", ".partial")):
                    try:
                        os.remove(os.path.join(dl, f))
                        count += 1
                    except:
                        pass
            success(f"已清理 [bold]{count}[/bold] 个未完成下载")
            pause()

        elif choice == "4":
            dirs = [
                os.path.join(os.path.expanduser("~"), d)
                for d in ("Downloads", "Desktop", "Documents")
            ]
            count = 0
            with Progress(SpinnerColumn(), TextColumn("扫描中..."), transient=True) as p:
                p.add_task("", total=None)
                for base in dirs:
                    for root, _, _ in os.walk(base, topdown=False):
                        if root == base:
                            continue
                        try:
                            if not os.listdir(root):
                                os.rmdir(root)
                                count += 1
                        except:
                            pass
            success(f"已清理 [bold]{count}[/bold] 个空文件夹")
            pause()

        elif choice == "5":
            script = os.path.join(script_dir, "pdf_merger.py")
            if os.path.exists(script):
                subprocess.Popen(f'start cmd /k python "{script}"', shell=True)
                success("已启动 PDF 合并工具")
            else:
                error("未找到 pdf_merger.py")
            pause()

        elif choice == "6":
            _register_context_menu(True)
            pause()

        elif choice == "7":
            _register_context_menu(False)
            pause()


def _register_context_menu(enable):
    """注册或卸载右键菜单"""
    python_exe = sys.executable
    script = os.path.join(SCRIPT_DIR, "file_info.py")
    cmd = f'"{python_exe}" "{script}" "%1"'

    keys = [
        r"*\shell\查看文件说明",           # 所有文件
        r"Directory\shell\查看文件说明",    # 文件夹
    ]
    try:
        for key_path in keys:
            if enable:
                key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path)
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "查看文件说明 (AI)")
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, "shell32.dll,21")
                winreg.CloseKey(key)
                cmd_key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path + r"\command")
                winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, cmd)
                winreg.CloseKey(cmd_key)
            else:
                for sub in [r"\command", ""]:
                    try:
                        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, key_path + sub)
                    except:
                        pass
        if enable:
            success("右键菜单注册成功，右键任意文件/文件夹即可看到「查看文件说明」")
            info("首次使用未知文件时 AI 需要几秒思考，请稍等")
        else:
            success("右键菜单已卸载")
    except PermissionError:
        error("需要管理员权限，请以管理员身份运行 cmd 后重试")

# ── 文件夹说明库 ──────────────────────────────────────

# 风险等级: safe=可安全删除, caution=谨慎, danger=禁止删除
FOLDER_INFO = {
    # C盘根目录
    "windows":              ("Windows 系统核心文件", "danger"),
    "program files":        ("64位应用程序安装目录", "caution"),
    "program files (x86)":  ("32位应用程序安装目录", "caution"),
    "programdata":          ("应用程序公共数据（配置/日志等）", "caution"),
    "users":                ("所有用户的个人文件夹", "caution"),
    "recovery":             ("系统恢复分区文件", "danger"),
    "$recycle.bin":         ("回收站", "safe"),
    "system volume information": ("系统还原点数据", "danger"),
    "pagefile.sys":         ("虚拟内存页面文件", "danger"),
    "hiberfil.sys":         ("休眠文件", "caution"),
    "swapfile.sys":         ("现代应用虚拟内存", "danger"),

    # Windows 子目录
    "system32":             ("32/64位系统核心DLL和驱动", "danger"),
    "syswow64":             ("32位兼容层系统文件", "danger"),
    "temp":                 ("系统临时文件，可清理", "safe"),
    "prefetch":             ("程序预读缓存，可清理", "safe"),
    "installer":            ("已安装程序的缓存包，勿删", "danger"),
    "drivers":              ("硬件驱动文件", "danger"),
    "fonts":                ("系统字体文件", "caution"),
    "logs":                 ("系统日志，可清理", "safe"),
    "winsxs":               ("系统组件备份，勿删", "danger"),
    "softwaredistribution":  ("Windows Update 下载缓存，可清理", "safe"),

    # 用户目录
    "desktop":              ("桌面文件", "safe"),
    "documents":            ("我的文档", "safe"),
    "downloads":            ("下载文件夹", "safe"),
    "pictures":             ("图片文件夹", "safe"),
    "videos":               ("视频文件夹", "safe"),
    "music":                ("音乐文件夹", "safe"),
    "appdata":              ("应用程序用户数据（含配置和缓存）", "caution"),
    "local":                ("本地应用数据（含缓存，部分可清理）", "caution"),
    "roaming":              ("漫游应用数据（软件配置，勿随意删）", "caution"),
    "locallow":             ("低权限应用数据（如浏览器缓存）", "caution"),
    "temp":                 ("用户临时文件，可清理", "safe"),

    # ProgramData 常见子目录
    "microsoft":            ("微软产品数据", "caution"),
    "package cache":        ("Visual C++ 等运行库缓存", "caution"),

    # 常见软件残留
    "crash reports":        ("程序崩溃报告，可删除", "safe"),
    "logs":                 ("日志文件，可删除", "safe"),
    "cache":                ("缓存文件，可清理", "safe"),
    "updater":              ("自动更新程序", "caution"),
}

RISK_STYLE = {
    "safe":    ("[green]✓ 可清理[/green]",   "green"),
    "caution": ("[yellow]⚠ 谨慎[/yellow]",   "yellow"),
    "danger":  ("[red]✗ 禁止删除[/red]",     "red"),
}

def get_folder_info(name):
    key = name.lower().strip()
    if key in FOLDER_INFO:
        desc, risk = FOLDER_INFO[key]
        label, color = RISK_STYLE[risk]
        return desc, label, color
    return None, None, None


# ── 磁盘浏览 & 应用搜索 ───────────────────────────────

def get_drives():
    drives = []
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        d = f"{letter}:\\"
        if os.path.exists(d):
            drives.append(d)
    return drives


def browse_dir(path):
    while True:
        header(f"📁 {path}")
        try:
            entries = sorted(os.scandir(path), key=lambda e: (not e.is_dir(), e.name.lower()))
        except PermissionError:
            error("无权限访问此目录")
            pause()
            return

        dirs, files = [], []
        for e in entries:
            if e.is_dir():
                dirs.append(e)
            else:
                files.append(e)

        table = Table(box=box.SIMPLE_HEAVY, show_lines=False, expand=True)
        table.add_column("#", style="dim", width=5, justify="right")
        table.add_column("名称", min_width=28)
        table.add_column("说明", min_width=28, style="dim")
        table.add_column("风险", width=12)
        table.add_column("大小", width=10, justify="right")

        for i, e in enumerate(dirs, 1):
            desc, label, color = get_folder_info(e.name)
            table.add_row(
                str(i),
                f"[bold cyan]{e.name}[/bold cyan]",
                desc or "",
                label or "",
                "-"
            )
        for i, e in enumerate(files, len(dirs) + 1):
            try:
                size = f"{e.stat().st_size / 1024:.1f} KB"
            except:
                size = "-"
            desc, label, _ = get_folder_info(e.name)
            table.add_row(
                str(i),
                e.name,
                desc or "",
                label or "",
                size
            )

        console.print(table)
        console.print(f"\n[dim]共 {len(dirs)} 个文件夹，{len(files)} 个文件[/dim]")
        console.print("\n  输入序号进入文件夹  |  [cyan]o[/cyan] 用资源管理器打开  |  [cyan]0[/cyan] 返回\n")

        choice = Prompt.ask("[bold]请选择[/bold]").strip().lower()

        if choice == "0":
            break
        elif choice == "o":
            subprocess.Popen(f'explorer "{path}"', shell=True)
        else:
            try:
                idx = int(choice) - 1
                all_entries = dirs + files
                if 0 <= idx < len(dirs):
                    browse_dir(all_entries[idx].path)
                else:
                    error("只能进入文件夹")
                    pause()
            except ValueError:
                error("无效输入")
                pause()


def search_app_folders(keyword):
    """在所有盘符搜索包含关键词的文件夹"""
    drives = get_drives()
    # 常见应用安装/残留路径优先搜索
    priority_paths = []
    for d in drives:
        for sub in [
            "Program Files", "Program Files (x86)",
            "ProgramData", "Users",
            os.path.join("Users", os.getlogin(), "AppData", "Local"),
            os.path.join("Users", os.getlogin(), "AppData", "Roaming"),
            os.path.join("Users", os.getlogin(), "AppData", "LocalLow"),
        ]:
            p = os.path.join(d, sub)
            if os.path.isdir(p):
                priority_paths.append(p)

    results = []
    keyword_lower = keyword.lower()

    with Progress(SpinnerColumn(), TextColumn(f"搜索 [cyan]{keyword}[/cyan] 相关文件夹..."), transient=True) as p:
        task = p.add_task("", total=None)
        for base in priority_paths:
            try:
                for entry in os.scandir(base):
                    if entry.is_dir() and keyword_lower in entry.name.lower():
                        results.append(entry.path)
            except:
                pass
            # 再深一层
            try:
                for entry in os.scandir(base):
                    if not entry.is_dir():
                        continue
                    try:
                        for sub in os.scandir(entry.path):
                            if sub.is_dir() and keyword_lower in sub.name.lower():
                                results.append(sub.path)
                    except:
                        pass
            except:
                pass

    return results


def disk_explorer():
    while True:
        header("💽 磁盘浏览 & 应用搜索")
        console.print("  [cyan]1[/cyan]  浏览磁盘")
        console.print("  [cyan]2[/cyan]  搜索应用文件夹（含残留）")
        console.print("  [cyan]0[/cyan]  返回\n")
        choice = Prompt.ask("[bold]请选择[/bold]", choices=["0","1","2"], default="0")

        if choice == "0":
            break

        elif choice == "1":
            header("💽 选择磁盘")
            drives = get_drives()
            for i, d in enumerate(drives, 1):
                console.print(f"  [cyan]{i}[/cyan]  {d}")
            try:
                idx = int(Prompt.ask("选择盘符")) - 1
                if 0 <= idx < len(drives):
                    browse_dir(drives[idx])
            except ValueError:
                error("无效输入")
                pause()

        elif choice == "2":
            header("🔍 搜索应用文件夹")
            keyword = Prompt.ask("输入应用名关键词（如 WeChat、Adobe）")
            if not keyword.strip():
                continue

            results = search_app_folders(keyword.strip())

            if not results:
                info("未找到相关文件夹")
            else:
                table = Table(box=box.SIMPLE_HEAVY, show_lines=True)
                table.add_column("#", style="dim", width=5, justify="right")
                table.add_column("路径", style="white")
                for i, path in enumerate(results, 1):
                    table.add_row(str(i), path)
                console.print(table)
                console.print(f"\n[dim]共找到 {len(results)} 个相关文件夹[/dim]\n")

                action = Prompt.ask("输入序号用资源管理器打开，或按 [cyan]0[/cyan] 返回").strip()
                if action != "0":
                    try:
                        idx = int(action) - 1
                        if 0 <= idx < len(results):
                            subprocess.Popen(f'explorer "{results[idx]}"', shell=True)
                    except ValueError:
                        pass
            pause()


# ── 主菜单 ────────────────────────────────────────────

# ── 系统镜像备份 ──────────────────────────────────────

def is_admin():
    import ctypes
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def get_removable_drives():
    """获取所有可移动/外接磁盘"""
    import ctypes
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for i, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        if bitmask & (1 << i):
            d = f"{letter}:\\"
            dtype = ctypes.windll.kernel32.GetDriveTypeW(d)
            # 2=可移动 3=固定 4=网络 5=光驱
            if dtype in (2, 3):
                try:
                    free  = shutil.disk_usage(d).free  // (1024**3)
                    total = shutil.disk_usage(d).total // (1024**3)
                    label = f"{letter}: ({free}GB 可用 / {total}GB)"
                    drives.append((d, label, dtype))
                except:
                    pass
    return drives


# ── 工具管理 ──────────────────────────────────────────

TOOLS_JSON = os.path.join(SCRIPT_DIR, "tools.json")

def load_tools():
    if os.path.exists(TOOLS_JSON):
        import json
        with open(TOOLS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_tools(tools):
    import json
    with open(TOOLS_JSON, "w", encoding="utf-8") as f:
        json.dump(tools, f, ensure_ascii=False, indent=2)

def launch_tool(tool):
    path = tool["path"]
    ext  = os.path.splitext(path)[1].lower()
    if not os.path.exists(path):
        error(f"文件不存在: {path}")
        return
    if ext == ".py":
        subprocess.Popen(f'start cmd /k python "{path}"', shell=True)
    elif ext == ".jar":
        subprocess.Popen(f'start cmd /k java -jar "{path}"', shell=True)
    elif ext == ".exe":
        subprocess.Popen(f'"{path}"', shell=True)
    elif ext in (".bat", ".cmd"):
        subprocess.Popen(f'start cmd /k "{path}"', shell=True)
    elif ext == ".sh":
        subprocess.Popen(f'bash "{path}"', shell=True)
    else:
        subprocess.Popen(f'start "" "{path}"', shell=True)
    success(f"已启动: {tool['name']}")

def tool_manager():
    while True:
        header("🔧 工具管理")
        tools = load_tools()

        if tools:
            table = Table(box=box.SIMPLE_HEAVY, show_lines=False, expand=True)
            table.add_column("#", style="dim", width=5, justify="right")
            table.add_column("名称", min_width=20)
            table.add_column("类型", width=8)
            table.add_column("路径", style="dim", min_width=25)
            table.add_column("描述", style="dim")
            for i, t in enumerate(tools, 1):
                ext = os.path.splitext(t["path"])[1].upper() or "未知"
                exists = "[green]●[/green]" if os.path.exists(t["path"]) else "[red]✗[/red]"
                table.add_row(str(i), f"{exists} {t['name']}", ext, t["path"], t.get("desc", ""))
            console.print(table)
        else:
            info("暂无工具，请先添加")

        console.print("\n  [cyan]a[/cyan]  添加工具（拖入文件夹/文件）")
        console.print("  [cyan]r[/cyan]  启动工具")
        console.print("  [cyan]d[/cyan]  删除工具")
        console.print("  [cyan]e[/cyan]  编辑工具信息")
        console.print("  [cyan]0[/cyan]  返回\n")
        choice = Prompt.ask("[bold]请选择[/bold]").strip().lower()

        if choice == "0":
            break

        elif choice == "a":
            header("➕ 添加工具")
            console.print("[dim]将文件或文件夹拖入终端，按回车确认[/dim]\n")
            raw = input("拖入路径: ").strip().strip('"')
            if not raw or not os.path.exists(raw):
                error("路径不存在")
                pause()
                continue
            name = Prompt.ask("工具名称", default=os.path.basename(raw))
            desc = Prompt.ask("简短描述（可留空）", default="")
            tools.append({"name": name, "path": raw, "desc": desc})
            save_tools(tools)
            success(f"已添加: {name}")
            pause()

        elif choice == "r":
            if not tools:
                error("没有可启动的工具")
                pause()
                continue
            try:
                idx = int(Prompt.ask("启动第几个")) - 1
                if 0 <= idx < len(tools):
                    launch_tool(tools[idx])
                else:
                    error("序号超出范围")
            except ValueError:
                error("无效输入")
            pause()

        elif choice == "d":
            if not tools:
                pause()
                continue
            try:
                idx = int(Prompt.ask("删除第几个（0取消）")) - 1
                if 0 <= idx < len(tools):
                    name = tools[idx]["name"]
                    if Confirm.ask(f"确认从列表删除 [bold red]{name}[/bold red]？（不会删除文件本身）"):
                        tools.pop(idx)
                        save_tools(tools)
                        success(f"已移除: {name}")
            except ValueError:
                error("无效输入")
            pause()

        elif choice == "e":
            if not tools:
                pause()
                continue
            try:
                idx = int(Prompt.ask("编辑第几个")) - 1
                if 0 <= idx < len(tools):
                    t = tools[idx]
                    t["name"] = Prompt.ask("新名称", default=t["name"])
                    t["desc"] = Prompt.ask("新描述", default=t.get("desc", ""))
                    save_tools(tools)
                    success("已更新")
            except ValueError:
                error("无效输入")
            pause()


def backup_manager():    while True:
        header("💾 系统镜像备份")
        console.print("  [cyan]1[/cyan]  创建系统镜像（备份到移动硬盘）")
        console.print("  [cyan]2[/cyan]  查看已有备份")
        console.print("  [cyan]3[/cyan]  如何从镜像恢复系统")
        console.print("  [cyan]0[/cyan]  返回\n")
        choice = Prompt.ask("[bold]请选择[/bold]", choices=["0","1","2","3"], default="0")

        if choice == "0":
            break

        elif choice == "1":
            header("💾 创建系统镜像")

            if not is_admin():
                console.print(Panel(
                    "[bold red]需要管理员权限[/bold red]\n\n"
                    "请关闭当前窗口，右键 cmd 选择[bold]「以管理员身份运行」[/bold]，\n"
                    "再输入 [cyan]中心[/cyan] 重新进入。",
                    box=box.ROUNDED
                ))
                pause()
                continue

            drives = get_removable_drives()
            if not drives:
                error("未检测到可用磁盘")
                pause()
                continue

            console.print("检测到以下磁盘：\n")
            for i, (_, label, dtype) in enumerate(drives, 1):
                tag = "[yellow]外接[/yellow]" if dtype == 2 else "[dim]本地[/dim]"
                console.print(f"  [cyan]{i}[/cyan]  {tag}  {label}")

            try:
                idx = int(Prompt.ask("\n选择目标磁盘序号（0取消）")) - 1
                if idx < 0 or idx >= len(drives):
                    continue
            except ValueError:
                continue

            target_drive, target_label, _ = drives[idx]

            console.print(Panel(
                f"[bold yellow]⚠ 注意[/bold yellow]\n\n"
                f"将把 [bold]整个系统（C盘）[/bold] 备份到：\n"
                f"[cyan]{target_drive}[/cyan]\n\n"
                f"• 备份期间请勿关机或拔出硬盘\n"
                f"• 备份文件较大，请确保目标盘空间充足\n"
                f"• 备份过程可能需要 30 分钟到数小时",
                box=box.ROUNDED
            ))

            if not Confirm.ask("确认开始备份？"):
                info("已取消")
                pause()
                continue

            # wbAdmin 命令：备份 C 盘系统到目标盘
            target = target_drive.rstrip("\\")
            cmd = f'wbAdmin start backup -backupTarget:{target} -include:C: -allCritical -quiet'

            console.print(f"\n[dim]执行命令: {cmd}[/dim]\n")
            info("备份已启动，请在新窗口中查看进度...")
            subprocess.Popen(f'start cmd /k {cmd}', shell=True)
            pause()

        elif choice == "2":
            header("📋 查看已有备份")
            drives = get_removable_drives()
            found = False
            for d, label, _ in drives:
                backup_path = os.path.join(d, "WindowsImageBackup")
                if os.path.isdir(backup_path):
                    found = True
                    console.print(f"[green]✓[/green] 在 [cyan]{d}[/cyan] 找到备份：")
                    try:
                        for entry in os.scandir(backup_path):
                            if entry.is_dir():
                                console.print(f"    📁 {entry.name}")
                                for sub in os.scandir(entry.path):
                                    if sub.is_dir():
                                        try:
                                            mtime = datetime.datetime.fromtimestamp(
                                                sub.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                                            console.print(f"       [dim]{sub.name}  {mtime}[/dim]")
                                        except:
                                            pass
                    except:
                        pass
            if not found:
                info("未在任何磁盘找到 Windows 镜像备份")
            pause()

        elif choice == "3":
            header("📖 如何从镜像恢复系统")
            console.print(Panel(
                "[bold]方法一：系统能正常启动时[/bold]\n"
                "  1. 插入备份所在的移动硬盘\n"
                "  2. 打开「控制面板」→「备份和还原(Windows 7)」\n"
                "  3. 点击「恢复系统设置或计算机」→「高级恢复方法」\n"
                "  4. 选择「使用之前创建的系统映像恢复计算机」\n\n"
                "[bold]方法二：系统崩溃无法启动时[/bold]\n"
                "  1. 插入 Windows 安装U盘，从U盘启动\n"
                "  2. 在安装界面选择「修复计算机」\n"
                "  3. 选择「疑难解答」→「系统映像恢复」\n"
                "  4. 插入备份硬盘，按提示选择镜像还原\n\n"
                "[dim]提示：建议提前制作一个 Windows 恢复U盘备用[/dim]",
                box=box.ROUNDED, padding=(1, 2)
            ))
            pause()


# ── 主菜单 ────────────────────────────────────────────

def main():
    while True:
        clear()
        console.print(Panel.fit(
            "[bold cyan]应用管理中心[/bold cyan]\n[dim]管理应用 · 环境变量 · 文件 · 磁盘 · 备份[/dim]",
            box=box.DOUBLE_EDGE, padding=(1, 4)
        ))
        console.print()
        console.print("  [cyan]1[/cyan]  📦  应用管理")
        console.print("  [cyan]2[/cyan]  🔧  环境变量管理")
        console.print("  [cyan]3[/cyan]  🗂   零散文件管理")
        console.print("  [cyan]4[/cyan]  💽  磁盘浏览 & 应用搜索")
        console.print("  [cyan]5[/cyan]  💾  系统镜像备份")
        console.print("  [cyan]6[/cyan]  🛠   工具管理")
        console.print("  [cyan]0[/cyan]  退出\n")
        choice = Prompt.ask("[bold]请选择[/bold]", choices=["0","1","2","3","4","5","6"], default="0")

        if choice == "0":
            console.print("\n[dim]再见 👋[/dim]\n")
            break
        elif choice == "1":
            app_manager()
        elif choice == "2":
            env_manager()
        elif choice == "3":
            file_manager()
        elif choice == "4":
            disk_explorer()
        elif choice == "5":
            backup_manager()
        elif choice == "6":
            tool_manager()

if __name__ == "__main__":
    main()
