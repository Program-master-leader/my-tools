#!/usr/bin/env python3
"""应用管理中心 - 图形界面"""

import os
import sys
import json
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_JSON = os.path.join(SCRIPT_DIR, "tools.json")

def resolve_path(path):
    """相对路径转绝对路径"""
    if os.path.isabs(path):
        return path
    return os.path.join(SCRIPT_DIR, path)

# ── 颜色主题 ──────────────────────────────────────────
BG       = "#1e1e2e"
BG2      = "#2a2a3e"
BG3      = "#313145"
ACCENT   = "#7c9ef8"
ACCENT2  = "#a6e3a1"
DANGER   = "#f38ba8"
TEXT     = "#cdd6f4"
TEXT_DIM = "#6c7086"
BTN_BG   = "#45475a"
BTN_HOV  = "#585b70"

def load_tools():
    if os.path.exists(TOOLS_JSON):
        with open(TOOLS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_tools(tools):
    with open(TOOLS_JSON, "w", encoding="utf-8") as f:
        json.dump(tools, f, ensure_ascii=False, indent=2)

def launch_tool(tool):
    path = resolve_path(tool["path"])
    ext  = os.path.splitext(path)[1].lower()
    if not os.path.exists(path):
        messagebox.showerror("错误", f"文件不存在:\n{path}")
        return
    if ext == ".py":
        subprocess.Popen(f'start cmd /k python "{path}"', shell=True)
    elif ext == ".jar":
        subprocess.Popen(f'start cmd /k java -jar "{path}"', shell=True)
    elif ext == ".exe":
        subprocess.Popen(f'"{path}"', shell=True)
    elif ext in (".bat", ".cmd"):
        subprocess.Popen(f'start cmd /k "{path}"', shell=True)
    else:
        subprocess.Popen(f'start "" "{path}"', shell=True)


class StyledButton(tk.Button):
    def __init__(self, master, text, command=None, color=BTN_BG, **kw):
        super().__init__(master, text=text, command=command,
                         bg=color, fg=TEXT, relief="flat",
                         font=("微软雅黑", 10), padx=12, pady=6,
                         cursor="hand2", activebackground=BTN_HOV,
                         activeforeground=TEXT, **kw)
        self.bind("<Enter>", lambda e: self.config(bg=BTN_HOV))
        self.bind("<Leave>", lambda e: self.config(bg=color))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("应用管理中心")
        self.geometry("900x620")
        self.configure(bg=BG)
        self.resizable(True, True)
        self._build_ui()
        self.refresh_tools()

    def _build_ui(self):
        # 顶部标题栏
        top = tk.Frame(self, bg=BG2, pady=12)
        top.pack(fill="x")
        tk.Label(top, text="⚙  应用管理中心", bg=BG2, fg=ACCENT,
                 font=("微软雅黑", 16, "bold")).pack(side="left", padx=20)

        # 左侧导航
        nav = tk.Frame(self, bg=BG2, width=160)
        nav.pack(side="left", fill="y")
        nav.pack_propagate(False)

        tk.Label(nav, text="功能模块", bg=BG2, fg=TEXT_DIM,
                 font=("微软雅黑", 9)).pack(pady=(20, 8))

        self.pages = {}
        nav_items = [
            ("🛠  工具管理", "tools"),
            ("🗂  文件清理", "clean"),
            ("🔧  环境变量", "env"),
            ("💾  系统备份", "backup"),
        ]
        self.nav_btns = {}
        for label, key in nav_items:
            btn = tk.Button(nav, text=label, bg=BG2, fg=TEXT,
                            relief="flat", font=("微软雅黑", 10),
                            anchor="w", padx=16, pady=8, cursor="hand2",
                            activebackground=BG3, activeforeground=ACCENT,
                            command=lambda k=key: self.show_page(k))
            btn.pack(fill="x")
            self.nav_btns[key] = btn

        # 主内容区
        self.content = tk.Frame(self, bg=BG)
        self.content.pack(side="left", fill="both", expand=True)

        self._build_tools_page()
        self._build_clean_page()
        self._build_env_page()
        self._build_backup_page()

        self.show_page("tools")

    def show_page(self, key):
        for k, frame in self.pages.items():
            frame.pack_forget()
            self.nav_btns[k].config(bg=BG2, fg=TEXT)
        self.pages[key].pack(fill="both", expand=True)
        self.nav_btns[key].config(bg=BG3, fg=ACCENT)

    # ── 工具管理页 ────────────────────────────────────

    def _build_tools_page(self):
        frame = tk.Frame(self.content, bg=BG)
        self.pages["tools"] = frame

        # 工具栏
        bar = tk.Frame(frame, bg=BG, pady=10)
        bar.pack(fill="x", padx=16)
        tk.Label(bar, text="🛠  工具管理", bg=BG, fg=TEXT,
                 font=("微软雅黑", 13, "bold")).pack(side="left")
        StyledButton(bar, "＋ 添加工具", self.add_tool, ACCENT).pack(side="right", padx=4)
        StyledButton(bar, "▶ 启动", self.run_tool).pack(side="right", padx=4)
        StyledButton(bar, "✎ 编辑", self.edit_tool).pack(side="right", padx=4)
        StyledButton(bar, "✕ 删除", self.delete_tool, DANGER).pack(side="right", padx=4)
        StyledButton(bar, "⬇ 下载", self.download_tool, "#89b4fa").pack(side="right", padx=4)

        # 拖拽提示
        tk.Label(frame, text="提示：点击「添加工具」或将文件路径粘贴添加",
                 bg=BG, fg=TEXT_DIM, font=("微软雅黑", 9)).pack(anchor="w", padx=16)

        # 列表
        cols = ("名称", "类型", "描述", "路径", "状态")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Custom.Treeview",
                        background=BG2, foreground=TEXT,
                        fieldbackground=BG2, rowheight=32,
                        font=("微软雅黑", 10))
        style.configure("Custom.Treeview.Heading",
                        background=BG3, foreground=ACCENT,
                        font=("微软雅黑", 10, "bold"))
        style.map("Custom.Treeview", background=[("selected", BG3)],
                  foreground=[("selected", ACCENT)])

        tree_frame = tk.Frame(frame, bg=BG)
        tree_frame.pack(fill="both", expand=True, padx=16, pady=8)

        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                  style="Custom.Treeview")
        widths = [160, 70, 180, 280, 60]
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, minwidth=50)

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", lambda e: self.run_tool())

    def refresh_tools(self):
        self.tools = load_tools()
        self.tree.delete(*self.tree.get_children())
        for t in self.tools:
            abs_path = resolve_path(t["path"])
            ext    = os.path.splitext(t["path"])[1].upper() or "文件夹"
            exists = os.path.exists(abs_path)
            has_url = t.get("url") or t.get("url_backup")
            status = "✓ 正常" if exists else "⬇ 可下载" if has_url else "✗ 丢失"
            tag    = "ok" if exists else "missing"
            self.tree.insert("", "end", values=(
                t["name"], ext, t.get("desc", ""), t["path"], status), tags=(tag,))
        self.tree.tag_configure("ok",      foreground=TEXT)
        self.tree.tag_configure("missing", foreground=DANGER)

    def _selected_idx(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一个工具")
            return None
        return self.tree.index(sel[0])

    def add_tool(self):
        choice = messagebox.askquestion("添加工具", "添加文件还是文件夹？\n\n是 = 文件/快捷方式\n否 = 文件夹")
        if choice == "yes":
            path = filedialog.askopenfilename(
                title="选择工具文件或快捷方式",
                filetypes=[("所有支持的文件", "*.py *.jar *.exe *.bat *.cmd *.sh *.lnk"),
                           ("所有文件", "*.*")])
        else:
            path = filedialog.askdirectory(title="选择工具文件夹或项目目录")
        if not path:
            return

        # 解析快捷方式，取真实路径
        real_path = path
        if path.lower().endswith(".lnk"):
            try:
                import winreg
                shell = __import__("win32com.client", fromlist=["Dispatch"]).Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(path)
                target = shortcut.Targetpath
                if target and os.path.exists(target):
                    real_path = target
                    # 如果目标是文件，取其所在目录作为项目根目录
                    if os.path.isfile(target):
                        project_dir = os.path.dirname(target)
                        use_dir = messagebox.askyesno(
                            "纳入项目管理",
                            f"检测到快捷方式指向：\n{target}\n\n"
                            f"是否将整个项目目录纳入管理？\n{project_dir}\n\n"
                            f"是 = 管理整个项目目录\n否 = 只管理此文件")
                        if use_dir:
                            real_path = project_dir
            except Exception:
                pass

        default_name = os.path.basename(real_path)
        name = simpledialog.askstring("工具名称", "请输入名称：", initialvalue=default_name)
        if not name:
            return
        desc = simpledialog.askstring("描述", "简短描述（可留空）：") or ""
        github_url = simpledialog.askstring(
            "下载地址（可选）",
            "文件不存在时的下载直链\n（留空跳过）：") or ""

        self.tools.append({"name": name, "path": real_path, "desc": desc, "url": github_url})
        save_tools(self.tools)
        self.refresh_tools()

    def download_tool(self):
        idx = self._selected_idx()
        if idx is None:
            return
        t = self.tools[idx]
        abs_path = resolve_path(t["path"])
        if os.path.exists(abs_path):
            messagebox.showinfo("提示", "文件已存在，无需下载")
            return
        url      = t.get("url", "")
        url_bak  = t.get("url_backup", "")
        if not url and not url_bak:
            messagebox.showwarning("无下载地址", f"「{t['name']}」没有配置下载地址")
            return

        import urllib.request, threading
        def do_download():
            os.makedirs(os.path.dirname(abs_path) or SCRIPT_DIR, exist_ok=True)
            for src, label in [(url, "GitHub"), (url_bak, "Gitee")]:
                if not src:
                    continue
                try:
                    urllib.request.urlretrieve(src, abs_path)
                    self.after(0, lambda l=label: [
                        messagebox.showinfo("下载完成", f"「{t['name']}」从 {l} 下载成功"),
                        self.refresh_tools()
                    ])
                    return
                except Exception:
                    continue
            self.after(0, lambda: messagebox.showerror("下载失败", "GitHub 和 Gitee 均无法访问，请检查网络"))

        messagebox.showinfo("开始下载", f"正在下载「{t['name']}」，请稍候...")
        threading.Thread(target=do_download, daemon=True).start()

    def run_tool(self):
        idx = self._selected_idx()
        if idx is None:
            return
        launch_tool(self.tools[idx])

    def edit_tool(self):
        idx = self._selected_idx()
        if idx is None:
            return
        t = self.tools[idx]
        name = simpledialog.askstring("编辑名称", "工具名称：", initialvalue=t["name"])
        if name:
            t["name"] = name
        desc = simpledialog.askstring("编辑描述", "工具描述：", initialvalue=t.get("desc", ""))
        if desc is not None:
            t["desc"] = desc
        save_tools(self.tools)
        self.refresh_tools()

    def delete_tool(self):
        idx = self._selected_idx()
        if idx is None:
            return
        name = self.tools[idx]["name"]
        if messagebox.askyesno("确认删除", f"从列表移除「{name}」？\n（不会删除文件本身）"):
            self.tools.pop(idx)
            save_tools(self.tools)
            self.refresh_tools()

    # ── 文件清理页 ────────────────────────────────────

    def _build_clean_page(self):
        frame = tk.Frame(self.content, bg=BG)
        self.pages["clean"] = frame
        tk.Label(frame, text="🗂  文件清理", bg=BG, fg=TEXT,
                 font=("微软雅黑", 13, "bold")).pack(anchor="w", padx=16, pady=12)

        self.clean_log = tk.Text(frame, bg=BG2, fg=TEXT, font=("Consolas", 10),
                                  relief="flat", state="disabled", height=15)
        self.clean_log.pack(fill="both", expand=True, padx=16, pady=4)

        btn_frame = tk.Frame(frame, bg=BG)
        btn_frame.pack(pady=10)
        StyledButton(btn_frame, "清理临时文件", lambda: self._clean("temp")).pack(side="left", padx=6)
        StyledButton(btn_frame, "清理未完成下载", lambda: self._clean("dl")).pack(side="left", padx=6)
        StyledButton(btn_frame, "清理空文件夹", lambda: self._clean("empty")).pack(side="left", padx=6)
        StyledButton(btn_frame, "整理桌面", lambda: self._run_script("desktop_organizer.py")).pack(side="left", padx=6)

    def _log(self, msg):
        self.clean_log.config(state="normal")
        self.clean_log.insert("end", msg + "\n")
        self.clean_log.see("end")
        self.clean_log.config(state="disabled")

    def _clean(self, mode):
        import glob, tempfile, shutil
        if mode == "temp":
            temp = tempfile.gettempdir()
            count = 0
            for f in glob.glob(os.path.join(temp, "*.tmp")) + glob.glob(os.path.join(temp, "*.log")):
                try:
                    os.remove(f)
                    count += 1
                except:
                    pass
            self._log(f"✓ 清理临时文件 {count} 个")
        elif mode == "dl":
            dl = os.path.join(os.path.expanduser("~"), "Downloads")
            count = 0
            for f in os.listdir(dl):
                if f.endswith((".crdownload", ".part", ".partial")):
                    try:
                        os.remove(os.path.join(dl, f))
                        count += 1
                    except:
                        pass
            self._log(f"✓ 清理未完成下载 {count} 个")
        elif mode == "empty":
            dirs = [os.path.join(os.path.expanduser("~"), d)
                    for d in ("Downloads", "Desktop", "Documents")]
            count = 0
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
            self._log(f"✓ 清理空文件夹 {count} 个")

    def _run_script(self, name):
        script = os.path.join(SCRIPT_DIR, name)
        if os.path.exists(script):
            subprocess.Popen(f'python "{script}"', shell=True)
            self._log(f"✓ 已启动 {name}")
        else:
            self._log(f"✗ 未找到 {name}")

    # ── 环境变量页 ────────────────────────────────────

    def _build_env_page(self):
        import winreg
        frame = tk.Frame(self.content, bg=BG)
        self.pages["env"] = frame
        tk.Label(frame, text="🔧  环境变量", bg=BG, fg=TEXT,
                 font=("微软雅黑", 13, "bold")).pack(anchor="w", padx=16, pady=12)

        btn_frame = tk.Frame(frame, bg=BG)
        btn_frame.pack(anchor="w", padx=16, pady=4)
        StyledButton(btn_frame, "刷新", self._load_env).pack(side="left", padx=4)
        StyledButton(btn_frame, "打开系统设置", lambda: subprocess.Popen(
            "rundll32 sysdm.cpl,EditEnvironmentVariables", shell=True)).pack(side="left", padx=4)

        cols = ("变量名", "值")
        style = ttk.Style()
        style.configure("Env.Treeview", background=BG2, foreground=TEXT,
                        fieldbackground=BG2, rowheight=28, font=("Consolas", 9))
        style.configure("Env.Treeview.Heading", background=BG3, foreground=ACCENT,
                        font=("微软雅黑", 10, "bold"))

        self.env_tree = ttk.Treeview(frame, columns=cols, show="headings", style="Env.Treeview")
        self.env_tree.heading("变量名", text="变量名")
        self.env_tree.heading("值", text="值")
        self.env_tree.column("变量名", width=200)
        self.env_tree.column("值", width=500)
        self.env_tree.pack(fill="both", expand=True, padx=16, pady=4)
        self._load_env()

    def _load_env(self):
        import winreg
        self.env_tree.delete(*self.env_tree.get_children())
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment")
            for i in range(winreg.QueryInfoKey(key)[1]):
                name, val, _ = winreg.EnumValue(key, i)
                self.env_tree.insert("", "end", values=(name, val))
        except:
            pass

    # ── 系统备份页 ────────────────────────────────────

    def _build_backup_page(self):
        frame = tk.Frame(self.content, bg=BG)
        self.pages["backup"] = frame

        # 标题栏
        bar = tk.Frame(frame, bg=BG, pady=10)
        bar.pack(fill="x", padx=16)
        tk.Label(bar, text="💾  系统备份", bg=BG, fg=TEXT,
                 font=("微软雅黑", 13, "bold")).pack(side="left")
        StyledButton(bar, "🔄 刷新", self._refresh_backups).pack(side="right", padx=4)

        # 备份类型选择
        type_frame = tk.LabelFrame(frame, text="备份类型", bg=BG, fg=ACCENT,
                                    font=("微软雅黑", 10), padx=12, pady=8)
        type_frame.pack(fill="x", padx=16, pady=6)

        self.backup_type = tk.StringVar(value="system")
        types = [
            ("完整系统备份（C盘 + D盘镜像）", "system"),
            ("仅系统盘备份（C盘数据）",       "conly"),
            ("所有 PDF 文件备份",             "pdf"),
            ("所有 Word 文档备份",            "word"),
        ]
        for label, val in types:
            tk.Radiobutton(type_frame, text=label, variable=self.backup_type,
                           value=val, bg=BG, fg=TEXT, selectcolor=BG3,
                           activebackground=BG, activeforeground=ACCENT,
                           font=("微软雅黑", 10)).pack(anchor="w", pady=2)

        # 操作按钮
        btn_frame = tk.Frame(frame, bg=BG)
        btn_frame.pack(fill="x", padx=16, pady=4)
        StyledButton(btn_frame, "▶ 开始备份", self._start_backup, ACCENT).pack(side="left", padx=4)
        StyledButton(btn_frame, "↩ 还原选中备份", self._restore_backup, "#89b4fa").pack(side="left", padx=4)
        StyledButton(btn_frame, "✕ 删除选中备份", self._delete_backup, DANGER).pack(side="left", padx=4)

        # 备份记录列表
        tk.Label(frame, text="备份记录", bg=BG, fg=TEXT_DIM,
                 font=("微软雅黑", 9)).pack(anchor="w", padx=16, pady=(8,2))

        cols = ("备份名称", "类型", "备份时间", "大小", "路径")
        style = ttk.Style()
        style.configure("Bak.Treeview", background=BG2, foreground=TEXT,
                        fieldbackground=BG2, rowheight=30, font=("微软雅黑", 10))
        style.configure("Bak.Treeview.Heading", background=BG3, foreground=ACCENT,
                        font=("微软雅黑", 10, "bold"))

        tree_frame = tk.Frame(frame, bg=BG)
        tree_frame.pack(fill="both", expand=True, padx=16, pady=4)
        self.bak_tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                      style="Bak.Treeview")
        widths = [180, 100, 150, 80, 280]
        for col, w in zip(cols, widths):
            self.bak_tree.heading(col, text=col)
            self.bak_tree.column(col, width=w, minwidth=50)
        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.bak_tree.yview)
        self.bak_tree.configure(yscrollcommand=sb.set)
        self.bak_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.backup_records = []
        self._refresh_backups()

    def _get_backup_dir(self):
        """读取或选择备份根目录"""
        cfg = os.path.join(SCRIPT_DIR, "backup_dir.txt")
        if os.path.exists(cfg):
            with open(cfg) as f:
                d = f.read().strip()
            if os.path.isdir(d):
                return d
        d = filedialog.askdirectory(title="选择备份保存位置（建议选移动硬盘）")
        if d:
            with open(cfg, "w") as f:
                f.write(d)
        return d

    def _refresh_backups(self):
        self.bak_tree.delete(*self.bak_tree.get_children())
        self.backup_records = []
        cfg = os.path.join(SCRIPT_DIR, "backup_dir.txt")
        if not os.path.exists(cfg):
            return
        with open(cfg) as f:
            base = f.read().strip()
        if not os.path.isdir(base):
            return

        type_labels = {
            "system": "完整系统", "conly": "系统盘",
            "pdf": "PDF文件", "word": "Word文档"
        }
        for name in sorted(os.listdir(base), reverse=True):
            path = os.path.join(base, name)
            if not os.path.isdir(path) and not os.path.isfile(path):
                continue
            # 只显示符合备份命名格式的条目: type_YYYYMMDD_HHMMSS
            parts = name.split("_")
            if len(parts) < 3:
                continue
            btype = parts[0]
            if btype not in ("system", "conly", "pdf", "word"):
                continue
            label = type_labels.get(btype, btype)
            try:
                import datetime
                ts = "_".join(name.split("_")[1:3])
                dt = datetime.datetime.strptime(ts, "%Y%m%d_%H%M%S")
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                time_str = "未知时间"
            try:
                if os.path.isdir(path):
                    size = sum(os.path.getsize(os.path.join(r, f))
                               for r, _, fs in os.walk(path) for f in fs)
                else:
                    size = os.path.getsize(path)
                size_str = f"{size/1024/1024:.1f} MB"
            except:
                size_str = "-"
            self.backup_records.append({"name": name, "path": path, "type": btype})
            self.bak_tree.insert("", "end", values=(name, label, time_str, size_str, path))

    def _start_backup(self):
        import ctypes, datetime, shutil, threading
        btype = self.backup_type.get()
        base  = self._get_backup_dir()
        if not base:
            return

        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"{btype}_{ts}"
        dst  = os.path.join(base, name)

        if btype in ("system", "conly"):
            if not ctypes.windll.shell32.IsUserAnAdmin():
                messagebox.showwarning("权限不足", "系统备份需要管理员权限\n请以管理员身份运行本程序")
                return
            drive = os.path.splitdrive(base)[0]
            if btype == "system":
                # 完整备份：C盘 + D盘
                cmd = f'wbAdmin start backup -backupTarget:{drive} -include:C:,D: -allCritical -quiet'
            else:
                # 仅系统盘：C盘
                cmd = f'wbAdmin start backup -backupTarget:{drive} -include:C: -allCritical -quiet'
            subprocess.Popen(f'start cmd /k {cmd}', shell=True)
            messagebox.showinfo("已启动", "系统备份已在新窗口启动，完成后请刷新列表")

        elif btype in ("pdf", "word"):
            ext = ".pdf" if btype == "pdf" else (".docx", ".doc")
            search_dirs = [
                os.path.expanduser("~\\Desktop"),
                os.path.expanduser("~\\Documents"),
                os.path.expanduser("~\\Downloads"),
            ]
            def do_backup():
                os.makedirs(dst, exist_ok=True)
                count = 0
                for d in search_dirs:
                    for root, _, files in os.walk(d):
                        for f in files:
                            if f.lower().endswith(ext):
                                try:
                                    shutil.copy2(os.path.join(root, f), dst)
                                    count += 1
                                except:
                                    pass
                self.after(0, lambda: [
                    messagebox.showinfo("备份完成", f"共备份 {count} 个文件\n保存到: {dst}"),
                    self._refresh_backups()
                ])
            threading.Thread(target=do_backup, daemon=True).start()
            messagebox.showinfo("备份中", "正在搜索并备份文件，请稍候...")

    def _restore_backup(self):
        sel = self.bak_tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一条备份记录")
            return
        idx  = self.bak_tree.index(sel[0])
        rec  = self.backup_records[idx]
        btype = rec["type"]

        if btype in ("system", "conly"):
            messagebox.showinfo("系统还原说明",
                "系统镜像还原步骤：\n\n"
                "方法一（系统可启动）：\n"
                "  控制面板 → 备份和还原 → 恢复系统设置\n\n"
                "方法二（系统崩溃）：\n"
                "  用Windows安装U盘启动 →\n"
                "  修复计算机 → 系统映像恢复")
        else:
            dst = filedialog.askdirectory(title="选择还原目标文件夹")
            if not dst:
                return
            import shutil, threading
            def do_restore():
                count = 0
                for f in os.listdir(rec["path"]):
                    try:
                        shutil.copy2(os.path.join(rec["path"], f), dst)
                        count += 1
                    except:
                        pass
                self.after(0, lambda: messagebox.showinfo("还原完成", f"共还原 {count} 个文件到:\n{dst}"))
            threading.Thread(target=do_restore, daemon=True).start()

    def _delete_backup(self):
        sel = self.bak_tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一条备份记录")
            return
        idx = self.bak_tree.index(sel[0])
        rec = self.backup_records[idx]
        if not messagebox.askyesno("确认删除", f"确认删除备份：\n{rec['name']}\n\n此操作不可恢复"):
            return
        import shutil
        try:
            if os.path.isdir(rec["path"]):
                shutil.rmtree(rec["path"])
            else:
                os.remove(rec["path"])
            self._refresh_backups()
            messagebox.showinfo("完成", "备份已删除")
        except Exception as e:
            messagebox.showerror("失败", str(e))


if __name__ == "__main__":
    app = App()
    app.mainloop()
