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
        choice = messagebox.askquestion("添加工具", "添加文件还是文件夹？\n\n是 = 文件\n否 = 文件夹")
        if choice == "yes":
            path = filedialog.askopenfilename(
                title="选择工具文件",
                filetypes=[("所有支持的文件", "*.py *.jar *.exe *.bat *.cmd *.sh"),
                           ("所有文件", "*.*")])
        else:
            path = filedialog.askdirectory(title="选择工具文件夹")
        if not path:
            return
        name = simpledialog.askstring("工具名称", "请输入工具名称：",
                                       initialvalue=os.path.basename(path))
        if not name:
            return
        desc = simpledialog.askstring("工具描述", "简短描述（可留空）：") or ""
        # 记录 GitHub 下载地址（可选）
        github_url = simpledialog.askstring(
            "下载地址（可选）",
            "如果文件不存在时需要从网络下载，请填写直链地址\n（留空跳过）：") or ""
        self.tools.append({"name": name, "path": path, "desc": desc, "url": github_url})
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
        tk.Label(frame, text="💾  系统备份", bg=BG, fg=TEXT,
                 font=("微软雅黑", 13, "bold")).pack(anchor="w", padx=16, pady=12)

        info = (
            "系统镜像备份使用 Windows 内置的 wbAdmin 工具\n\n"
            "• 需要以管理员身份运行\n"
            "• 备份整个 C 盘到指定磁盘\n"
            "• 系统崩溃后可从镜像还原\n\n"
            "建议将备份保存到移动硬盘"
        )
        tk.Label(frame, text=info, bg=BG2, fg=TEXT, font=("微软雅黑", 11),
                 justify="left", padx=20, pady=20).pack(padx=16, pady=8, fill="x")

        StyledButton(frame, "▶ 启动备份向导（需管理员）",
                     self._start_backup, ACCENT).pack(pady=10)

    def _start_backup(self):
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            messagebox.showwarning("权限不足", "请以管理员身份运行本程序后再使用备份功能")
            return
        target = filedialog.askdirectory(title="选择备份目标磁盘/文件夹")
        if not target:
            return
        drive = os.path.splitdrive(target)[0]
        cmd = f'wbAdmin start backup -backupTarget:{drive} -include:C: -allCritical -quiet'
        subprocess.Popen(f'start cmd /k {cmd}', shell=True)


if __name__ == "__main__":
    app = App()
    app.mainloop()
