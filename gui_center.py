#!/usr/bin/env python3
"""应用管理中心 - 图形界面"""

import os
import sys
import json
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog

# 尝试导入拖拽支持
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    _DND_OK = True
except ImportError:
    _DND_OK = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, "frozen", False):
    SCRIPT_DIR = os.path.dirname(sys.executable)

# 用户数据目录（AppData\Roaming\KHY小工具），不污染 exe 所在位置
_USER_DATA = os.path.join(os.environ.get("APPDATA", SCRIPT_DIR), "KHY小工具")
os.makedirs(_USER_DATA, exist_ok=True)

# tools.json：优先用户数据目录，没有则用内置
TOOLS_JSON = os.path.join(_USER_DATA, "tools.json")
_BUILTIN_TOOLS_JSON = os.path.join(
    getattr(sys, "_MEIPASS", SCRIPT_DIR), "tools.json")

# git_config.json 也存用户数据目录
GIT_CONFIG_JSON = os.path.join(_USER_DATA, "git_config.json")

def load_tools():
    # 优先用户目录（有用户自定义工具），否则用内置
    src = TOOLS_JSON if os.path.exists(TOOLS_JSON) else _BUILTIN_TOOLS_JSON
    if os.path.exists(src):
        with open(src, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_tools(tools):
    # 保存到 exe 同目录（不污染打包内部）
    with open(TOOLS_JSON, "w", encoding="utf-8") as f:
        json.dump(tools, f, ensure_ascii=False, indent=2)

def resolve_path(path):
    """相对路径转绝对路径，自动搜索常用目录"""
    if os.path.isabs(path):
        return path
    # 先在 SCRIPT_DIR 找
    candidate = os.path.join(SCRIPT_DIR, path)
    if os.path.exists(candidate):
        return candidate
    # 再搜常用路径
    search_roots = [
        r"D:\pdf小工具",
        r"C:\pdf小工具",
        os.path.expanduser("~\\Desktop"),
        os.path.expanduser("~\\Documents"),
        r"D:\工具",
        r"E:\工具",
        r"E:\pdf小工具",
    ]
    fname = os.path.basename(path)
    for root in search_roots:
        p = os.path.join(root, fname)
        if os.path.exists(p):
            return p
        # 也搜一层子目录
        p2 = os.path.join(root, path)
        if os.path.exists(p2):
            return p2
    return candidate  # 找不到返回默认路径（显示丢失）

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

def launch_tool(tool):
    path = resolve_path(tool["path"])
    ext  = os.path.splitext(path)[1].lower()
    if not os.path.exists(path):
        messagebox.showerror("错误", f"文件不存在:\n{path}")
        return
    cwd = os.path.dirname(path) or SCRIPT_DIR
    if ext == ".py":
        subprocess.Popen(["cmd", "/k", "python", path], cwd=cwd, shell=False)
    elif ext == ".jar":
        subprocess.Popen(["cmd", "/k", "java", "-jar", path], cwd=cwd, shell=False)
    elif ext == ".exe":
        subprocess.Popen([path], cwd=cwd, shell=False)
    elif ext in (".bat", ".cmd"):
        tmp = os.path.join(cwd, "_tmp_launch.bat")
        with open(tmp, "w") as f:
            f.write(f'@echo off\ncall "{path}"\n')
        def _run(tmp=tmp, cwd=cwd):
            subprocess.Popen(["cmd", "/k", tmp], cwd=cwd, shell=False)
            import time; time.sleep(2)
            try: os.unlink(tmp)
            except: pass
        threading.Thread(target=_run, daemon=True).start()
    else:
        subprocess.Popen(["cmd", "/c", "start", "", path], shell=False)


class StyledButton(tk.Button):
    def __init__(self, master, text, command=None, color=BTN_BG, **kw):
        super().__init__(master, text=text, command=command,
                         bg=color, fg=TEXT, relief="flat",
                         font=("微软雅黑", 10), padx=12, pady=6,
                         cursor="hand2", activebackground=BTN_HOV,
                         activeforeground=TEXT, **kw)
        self.bind("<Enter>", lambda e: self.config(bg=BTN_HOV))
        self.bind("<Leave>", lambda e: self.config(bg=color))


class App(TkinterDnD.Tk if _DND_OK else tk.Tk):
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
            ("🐙  Git 管理", "git"),
            ("🗂  文件清理", "clean"),
            ("🔧  环境变量", "env"),
            ("💾  系统备份", "backup"),
            ("🔑  账号管理", "accounts"),
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
        self._build_git_page()
        self._build_clean_page()
        self._build_env_page()
        self._build_backup_page()
        self._build_accounts_page()

        self.show_page("tools")

    # ── 账号管理页 ────────────────────────────────────

    def _build_accounts_page(self):
        frame = tk.Frame(self.content, bg=BG)
        self.pages["accounts"] = frame

        # 直接嵌入 account_manager 的 Frame，避免开新窗口
        try:
            from account_manager import AccountManagerFrame

            am = AccountManagerFrame(frame)
            am.pack(fill="both", expand=True)
        except Exception as e:
            tk.Label(
                frame,
                text="账号管理模块加载失败。\n请确认 account_manager.py 存在且无语法错误。\n\n"
                + str(e),
                bg=BG,
                fg=DANGER,
                font=("微软雅黑", 11),
                justify="left",
            ).pack(anchor="w", padx=16, pady=16)

            tk.Button(
                frame,
                text="▶ 以独立窗口打开账号管理",
                bg=ACCENT2,
                fg=BG,
                relief="flat",
                font=("微软雅黑", 10),
                padx=14,
                pady=8,
                cursor="hand2",
                command=lambda: self._open_account_manager_window(),
            ).pack(anchor="w", padx=16, pady=4)

    def _open_account_manager_window(self):
        try:
            import subprocess, sys, os

            path = os.path.join(SCRIPT_DIR, "account_manager.py")
            if os.path.exists(path):
                subprocess.Popen([sys.executable, path], cwd=SCRIPT_DIR, shell=False)
        except Exception:
            pass

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
        StyledButton(bar, "✎ 编辑", self.edit_tool).pack(side="right", padx=4)
        StyledButton(bar, "✕ 删除", self.delete_tool, DANGER).pack(side="right", padx=4)
        StyledButton(bar, "⬇ 下载", self.download_tool, "#89b4fa").pack(side="right", padx=4)

        # 拖拽提示
        if _DND_OK:
            drop_hint = "📂  将文件、文件夹或快捷方式拖拽到此处添加工具"
            drop_color = BG3
        else:
            drop_hint = "提示：点击「添加工具」选择文件/文件夹"
            drop_color = BG2
        self.drop_zone = tk.Label(frame, text=drop_hint, bg=drop_color, fg=TEXT_DIM,
            font=("微软雅黑", 9), pady=8, relief="flat", cursor="hand2")
        self.drop_zone.pack(fill="x", padx=16, pady=(0, 4))
        if _DND_OK:
            self.drop_zone.drop_target_register(DND_FILES)
            self.drop_zone.dnd_bind("<<Drop>>", self._on_drop)

        # 滚动卡片列表（支持每行内嵌启动按钮）
        container = tk.Frame(frame, bg=BG)
        container.pack(fill="both", expand=True, padx=16, pady=4)

        self._canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(container, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=sb.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._list_frame = tk.Frame(self._canvas, bg=BG)
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._list_frame, anchor="nw")
        self._list_frame.bind("<Configure>",
            lambda e: self._canvas.configure(
                scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>",
            lambda e: self._canvas.itemconfig(
                self._canvas_window, width=e.width))
        self._canvas.bind_all("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(-1*(e.delta//120), "units"))

        # 注册拖拽到 canvas 和 list_frame（修复拖拽失效）
        if _DND_OK:
            self._canvas.drop_target_register(DND_FILES)
            self._canvas.dnd_bind("<<Drop>>", self._on_drop)
            self._list_frame.drop_target_register(DND_FILES)
            self._list_frame.dnd_bind("<<Drop>>", self._on_drop)

        # 列头
        hdr = tk.Frame(self._list_frame, bg=BG3)
        hdr.pack(fill="x", pady=(0,2))
        for txt, w in [("名称",160),("描述",200),("路径",260),("状态",70),("操作",120)]:
            tk.Label(hdr, text=txt, bg=BG3, fg=ACCENT,
                     font=("微软雅黑",9,"bold"), width=w//8, anchor="w",
                     padx=6).pack(side="left")

        self._selected_idx_var = None

    def _on_drop(self, event):
        """处理拖拽进来的文件/文件夹"""
        raw = event.data.strip()
        # tkinterdnd2 返回的路径：多个文件用空格分隔，带空格的路径用{}包裹
        paths = []
        if raw.startswith("{"):
            import re
            paths = re.findall(r'\{([^}]+)\}|(\S+)', raw)
            paths = [a or b for a, b in paths]
        else:
            paths = raw.split()
        for p in paths:
            p = p.strip().strip('"')
            if p:
                self._process_path(p)

    def _resolve_lnk(self, lnk_path):
        """解析 .lnk 快捷方式，返回真实目标路径"""
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            sc = shell.CreateShortCut(lnk_path)
            target = sc.Targetpath
            if target and os.path.exists(target):
                return target
        except Exception:
            pass
        return None

    def _process_path(self, path):
        """统一处理一个路径（文件/文件夹/快捷方式），询问名称后加入列表"""
        real_path = path

        # 解析快捷方式
        if path.lower().endswith(".lnk"):
            target = self._resolve_lnk(path)
            if target:
                real_path = target
                if os.path.isfile(target):
                    project_dir = os.path.dirname(target)
                    ans = messagebox.askyesnocancel(
                        "纳入项目管理",
                        f"快捷方式指向：\n{target}\n\n"
                        f"是  → 管理整个项目目录：\n{project_dir}\n\n"
                        f"否  → 只管理此文件\n"
                        f"取消 → 跳过")
                    if ans is None:
                        return
                    if ans:
                        real_path = project_dir
            else:
                messagebox.showwarning("解析失败",
                    f"无法解析快捷方式目标路径\n{path}\n\n请确认已安装 pywin32")
                return

        # 检查是否已存在
        for t in self.tools:
            if os.path.normcase(resolve_path(t["path"])) == os.path.normcase(real_path):
                messagebox.showinfo("已存在", f"「{t['name']}」已在列表中")
                return

        default_name = os.path.basename(real_path.rstrip("\\/"))
        name = simpledialog.askstring("工具名称", f"路径：{real_path}\n\n请输入名称：",
                                       initialvalue=default_name)
        if not name:
            return
        desc = simpledialog.askstring("描述（可留空）", "简短描述这个工具的用途：") or ""

        # 计算大小，判断是否超出 Git 限制（50MB）
        pan_url = ""
        size_mb = self._get_path_size_mb(real_path)
        GIT_LIMIT_MB = 95  # 单文件限制：GitHub/Gitee 均为100MB，留5MB余量

        if size_mb > GIT_LIMIT_MB:
            ans = messagebox.askyesnocancel(
                "文件较大",
                f"「{name}」大小约 {size_mb:.0f} MB，超出单文件 Git 限制（100 MB）。\n\n"
                f"选择处理方式：\n"
                f"是  → 分卷压缩后上传 Git（自动切分为 <95MB 的分卷）\n"
                f"否  → 填写百度网盘链接备份\n"
                f"取消 → 只记录本地路径")
            if ans is None:
                pass  # 取消，只记录路径
            elif ans:
                # 分卷压缩上传
                self._split_and_sync(real_path, name)
                entry = {"name": name, "path": real_path, "desc": desc,
                         "url": "", "url_backup": ""}
                self.tools.append(entry)
                save_tools(self.tools)
                self.refresh_tools()
                return
            else:
                pan_url = simpledialog.askstring(
                    "百度网盘链接",
                    f"请将「{name}」上传到百度网盘后，\n粘贴分享链接（含提取码）：") or ""

        entry = {"name": name, "path": real_path, "desc": desc,
                 "url": "", "url_backup": ""}
        if pan_url:
            entry["pan_url"] = pan_url

        self.tools.append(entry)
        save_tools(self.tools)
        self.refresh_tools()

        # 小文件才同步到 Git
        if size_mb <= GIT_LIMIT_MB:
            self._git_sync(real_path, name)
        else:
            self._sync_toast(f"「{name}」较大，已跳过 Git 同步" +
                             ("，网盘链接已保存" if pan_url else ""))

    def _split_and_sync(self, src_path, tool_name):
        """分卷压缩大文件并推送到 Git，优先用7z，降级用zip"""
        import math, threading, shutil

        PART_SIZE = 90 * 1024 * 1024  # 90MB 每卷

        def find_7z():
            for p in ["7z",
                      r"D:\Program Files\7-Zip\7z.exe",
                      r"C:\Program Files\7-Zip\7z.exe",
                      r"C:\Program Files (x86)\7-Zip\7z.exe"]:
                try:
                    if subprocess.run([p, "i"], capture_output=True,
                                      timeout=3, creationflags=0x08000000
                                      ).returncode == 0:
                        return p
                except Exception:
                    pass
            return None

        def do():
            try:
                z7 = find_7z()
                safe_name = tool_name.replace(" ", "_")
                out_base = os.path.join(SCRIPT_DIR, f"_tmp_{safe_name}")

                if z7:
                    self.after(0, lambda: self._sync_toast(
                        f"正在7z压缩「{tool_name}」（可能需要几分钟）..."))
                    retcode = subprocess.call(
                        [z7, "a", "-t7z", "-mx=1", "-ssw", "-v90m",
                         f"{out_base}.7z", src_path],
                        creationflags=0x08000000)
                    if retcode > 1:
                        raise Exception(f"7z 返回错误码 {retcode}")
                    # 找生成的分卷文件
                    part_files = sorted([
                        os.path.join(SCRIPT_DIR, f)
                        for f in os.listdir(SCRIPT_DIR)
                        if f.startswith(f"_tmp_{safe_name}.7z")
                    ])
                else:
                    # 降级：Python zipfile 分卷
                    import zipfile
                    self.after(0, lambda: self._sync_toast(
                        f"未找到7z，使用zip压缩「{tool_name}」..."))
                    zip_path = f"{out_base}.zip"
                    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED,
                                         compresslevel=9) as zf:
                        if os.path.isdir(src_path):
                            for root, _, files in os.walk(src_path):
                                for f in files:
                                    fp = os.path.join(root, f)
                                    zf.write(fp, os.path.relpath(
                                        fp, os.path.dirname(src_path)))
                        else:
                            zf.write(src_path, os.path.basename(src_path))
                    # 手动分卷
                    zip_size = os.path.getsize(zip_path)
                    parts = math.ceil(zip_size / PART_SIZE)
                    part_files = []
                    with open(zip_path, "rb") as f:
                        for i in range(parts):
                            pf = f"{out_base}.z{i+1:02d}"
                            with open(pf, "wb") as out:
                                out.write(f.read(PART_SIZE))
                            part_files.append(pf)
                    os.unlink(zip_path)

                total_parts = len(part_files)
                self.after(0, lambda: self._sync_toast(
                    f"压缩完成，共 {total_parts} 卷，开始上传..."))

                for i, pf in enumerate(part_files):
                    fname = os.path.basename(pf)
                    dst = os.path.join(SCRIPT_DIR, fname)
                    if pf != dst:
                        shutil.move(pf, dst)
                    self._git_sync(dst, f"{tool_name} [{i+1}/{total_parts}]")

                self.after(0, lambda: self._sync_toast(
                    f"✓ 「{tool_name}」已分 {total_parts} 卷上传完成"))

            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._sync_toast(
                    f"分卷上传失败：{err[:100]}", ok=False))

        threading.Thread(target=do, daemon=True).start()

    def _get_git_status(self, tool):
        """检查工具文件是否已上传到 Git"""
        path = tool.get("path","")
        url  = tool.get("url","")
        url_bak = tool.get("url_backup","")

        # 有 Git URL 说明已配置上传
        if url or url_bak:
            return "☁ 已同步", ACCENT2

        # 检查是否是相对路径（在仓库目录内）
        if not os.path.isabs(path):
            abs_path = os.path.join(SCRIPT_DIR, path)
            # 用 git ls-files 检查是否被追踪
            git = self._find_git_exe()
            if git and os.path.exists(abs_path):
                try:
                    r = subprocess.run(
                        [git, "-C", SCRIPT_DIR, "ls-files", "--error-unmatch", path],
                        capture_output=True, timeout=3)
                    if r.returncode == 0:
                        return "☁ 已同步", ACCENT2
                    else:
                        return "⚠ 未追踪", "#f9e2af"
                except Exception:
                    pass

        # 绝对路径且无 URL，未上传
        return "— 本地", TEXT_DIM

    def _find_git_exe(self):
        for g in ["git", r"D:\Program Files\Git\cmd\git.exe",
                  r"C:\Program Files\Git\cmd\git.exe"]:
            try:
                if subprocess.run([g, "--version"], capture_output=True,
                                  timeout=3, creationflags=0x08000000
                                  ).returncode == 0:
                    return g
            except Exception:
                pass
        return None

    def _git_sync(self, src_path, tool_name):
        """把新增工具同步到 Git 仓库（优先 Gitee，失败只推 Gitee 也算成功）"""
        import shutil, threading

        # 动态找 git 可执行文件
        def find_git():
            for candidate in [
                "git",
                r"D:\Program Files\Git\cmd\git.exe",
                r"C:\Program Files\Git\cmd\git.exe",
            ]:
                try:
                    r = subprocess.run([candidate, "--version"],
                                       capture_output=True, timeout=3)
                    if r.returncode == 0:
                        return candidate
                except Exception:
                    continue
            return None

        def do_sync():
            git = find_git()
            if not git:
                self.after(0, lambda: self._sync_toast("未找到 git，跳过同步", ok=False))
                return

            # 如果文件/文件夹不在脚本目录内，先复制过来
            abs_src = os.path.abspath(src_path)
            script_abs = os.path.abspath(SCRIPT_DIR)
            if not abs_src.startswith(script_abs + os.sep) and abs_src != script_abs:
                base_name = os.path.basename(abs_src.rstrip("\\/"))
                dst = os.path.join(SCRIPT_DIR, base_name)
                try:
                    if os.path.isdir(abs_src):
                        if os.path.exists(dst):
                            shutil.rmtree(dst)
                        shutil.copytree(abs_src, dst)
                    else:
                        shutil.copy2(abs_src, dst)
                except Exception as e:
                    self.after(0, lambda: self._sync_toast(f"复制失败: {e}", ok=False))
                    return

            # git add + commit
            try:
                subprocess.run([git, "-C", SCRIPT_DIR, "add", "-A"],
                               capture_output=True)
                r = subprocess.run(
                    [git, "-C", SCRIPT_DIR, "commit", "-m", f"添加工具: {tool_name}"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace")
                if "nothing to commit" in r.stdout:
                    self.after(0, lambda: self._sync_toast("无变更，跳过推送"))
                    return
            except Exception as e:
                self.after(0, lambda: self._sync_toast(f"git commit 失败: {e}", ok=False))
                return

            # 先推 Gitee，再推 GitHub，任一成功即可
            for remote, label in [("gitee", "Gitee"), ("origin", "GitHub")]:
                r = subprocess.run(
                    [git, "-C", SCRIPT_DIR, "push", remote, "main"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace")
                if r.returncode == 0:
                    self.after(0, lambda l=label: self._sync_toast(f"已同步到 {l} ✓"))
                    return

            self.after(0, lambda: self._sync_toast("推送失败（网络问题），已保存本地 commit", ok=False))

        threading.Thread(target=do_sync, daemon=True).start()

    def _sync_toast(self, msg, ok=True):
        """在状态栏短暂显示同步结果"""
        color = ACCENT2 if ok else DANGER
        if not hasattr(self, "_toast_label"):
            self._toast_label = tk.Label(self, bg=BG, fg=color,
                                          font=("微软雅黑", 9), anchor="w")
            self._toast_label.pack(side="bottom", fill="x", padx=16, pady=2)
        self._toast_label.config(text=f"  Git: {msg}", fg=color)
        self.after(6000, lambda: self._toast_label.config(text=""))

    def refresh_tools(self):
        self.tools = load_tools()
        # 清空卡片列表
        for w in self._list_frame.winfo_children():
            if isinstance(w, tk.Frame) and w != self._list_frame:
                w.destroy()
        # 重新渲染列头后面的内容
        for widget in self._list_frame.winfo_children():
            widget.destroy()

        # 列头
        hdr = tk.Frame(self._list_frame, bg=BG3)
        hdr.pack(fill="x", pady=(0, 1))
        for txt, w in [("名称",18),("描述",22),("路径",28),("状态",8),("Git",8),("操作",14)]:
            tk.Label(hdr, text=txt, bg=BG3, fg=ACCENT,
                     font=("微软雅黑",9,"bold"), width=w, anchor="w",
                     padx=4).pack(side="left")

        self._row_frames = []
        for i, t in enumerate(self.tools):
            abs_path = resolve_path(t["path"])
            exists   = os.path.exists(abs_path)
            has_pan  = t.get("pan_url")
            has_git  = t.get("url") or t.get("url_backup")

            if exists:
                status_txt, status_fg = "✓ 正常", ACCENT2
            elif has_pan:
                status_txt, status_fg = "📦 网盘", "#f9e2af"
            elif has_git:
                status_txt, status_fg = "⬇ 可下载", ACCENT
            else:
                status_txt, status_fg = "✗ 丢失", DANGER

            row_bg = BG2 if i % 2 == 0 else BG3
            row = tk.Frame(self._list_frame, bg=row_bg, pady=4)
            row.pack(fill="x", pady=1)
            self._row_frames.append(row)

            # 点击行选中
            def _select(e, idx=i, r=row):
                for rf in self._row_frames:
                    rf.config(bg=BG2 if self._row_frames.index(rf) % 2 == 0 else BG3)
                r.config(bg="#3d3d5c")
                self._selected_idx_var = idx
            row.bind("<Button-1>", _select)

            # 名称
            tk.Label(row, text=t["name"], bg=row_bg, fg=TEXT,
                     font=("微软雅黑",10), width=18, anchor="w",
                     padx=4).pack(side="left")
            # 描述
            tk.Label(row, text=t.get("desc","")[:20], bg=row_bg, fg=TEXT_DIM,
                     font=("微软雅黑",9), width=22, anchor="w").pack(side="left")
            # 路径
            tk.Label(row, text=t["path"][:33], bg=row_bg, fg=TEXT_DIM,
                     font=("微软雅黑",9), width=28, anchor="w").pack(side="left")
            # 状态
            tk.Label(row, text=status_txt, bg=row_bg, fg=status_fg,
                     font=("微软雅黑",9), width=8, anchor="w").pack(side="left")
            # Git 状态
            git_txt, git_fg = self._get_git_status(t)
            tk.Label(row, text=git_txt, bg=row_bg, fg=git_fg,
                     font=("微软雅黑",9), width=8, anchor="w").pack(side="left")

            # 操作按钮区
            btn_area = tk.Frame(row, bg=row_bg)
            btn_area.pack(side="left", padx=4)

            # 判断是否可启动
            launch_path = t.get("launch") or t.get("launch_app") or (abs_path if exists else None)
            can_launch  = launch_path and os.path.exists(launch_path)

            if can_launch:
                def _launch(lp=launch_path, tn=t["name"]):
                    ext = os.path.splitext(lp)[1].lower()
                    cwd = os.path.dirname(lp) or SCRIPT_DIR
                    if ext == ".py":
                        subprocess.Popen(["cmd", "/k", "python", lp],
                                         cwd=cwd, shell=False)
                    elif ext in (".bat", ".cmd"):
                        tmp = os.path.join(cwd, "_tmp_launch.bat")
                        with open(tmp, "w") as f:
                            f.write(f'@echo off\ncall "{lp}"\n')
                        def _run_and_clean(tmp=tmp, cwd=cwd):
                            subprocess.Popen(["cmd", "/k", tmp], cwd=cwd, shell=False)
                            import time; time.sleep(2)
                            try: os.unlink(tmp)
                            except: pass
                        threading.Thread(target=_run_and_clean, daemon=True).start()
                    elif ext == ".exe":
                        subprocess.Popen([lp], cwd=cwd, shell=False)
                    elif os.path.isdir(lp):
                        subprocess.Popen(["explorer", lp], shell=False)
                    else:
                        subprocess.Popen(["cmd", "/c", "start", "", lp], shell=False)
                tk.Button(btn_area, text="▶ 启动", bg=ACCENT2, fg=BG,
                          relief="flat", font=("微软雅黑",9), padx=8, pady=3,
                          cursor="hand2", command=_launch).pack(side="left", padx=2)
            elif has_pan:
                def _open_pan(url=t["pan_url"]):
                    import webbrowser; webbrowser.open(url)
                tk.Button(btn_area, text="📦 网盘", bg="#f9e2af", fg=BG,
                          relief="flat", font=("微软雅黑",9), padx=8, pady=3,
                          cursor="hand2", command=_open_pan).pack(side="left", padx=2)
            elif has_git:
                tk.Button(btn_area, text="⬇ 下载", bg="#89b4fa", fg=BG,
                          relief="flat", font=("微软雅黑",9), padx=8, pady=3,
                          cursor="hand2",
                          command=lambda idx=i: self._download_by_idx(idx)
                          ).pack(side="left", padx=2)

            # ☁ 同步按钮：未同步到 Git 时显示
            if git_txt in ("⚠ 未追踪", "— 本地"):
                def _sync_tool(tool=t, path=abs_path):
                    size_mb = self._get_path_size_mb(path)
                    if size_mb > 95:
                        if messagebox.askyesno("文件较大",
                            f"「{tool['name']}」约 {size_mb:.0f} MB，超出单文件限制。\n\n"
                            f"是 → 自动7z分卷压缩后上传\n否 → 取消"):
                            self._split_and_sync(path, tool["name"])
                    else:
                        self._git_sync(path, tool["name"])
                tk.Button(btn_area, text="☁ 同步", bg="#89dceb", fg=BG,
                          relief="flat", font=("微软雅黑",9), padx=8, pady=3,
                          cursor="hand2", command=_sync_tool).pack(side="left", padx=2)

            # 绑定子控件点击也能选中行
            for child in row.winfo_children():
                if not isinstance(child, tk.Button):
                    child.bind("<Button-1>", _select)

    def _selected_idx(self):
        if self._selected_idx_var is None:
            messagebox.showwarning("提示", "请先点击选择一个工具")
            return None
        return self._selected_idx_var

    def add_tool(self):
        choice = messagebox.askquestion("添加工具", "添加文件还是文件夹？\n\n是 = 文件/快捷方式\n否 = 文件夹")
        if choice == "yes":
            path = filedialog.askopenfilename(
                title="选择工具文件或快捷方式",
                filetypes=[("所有支持的文件", "*.py *.jar *.exe *.bat *.cmd *.sh *.lnk"),
                           ("所有文件", "*.*")])
        else:
            path = filedialog.askdirectory(title="选择工具文件夹或项目目录")
        if path:
            self._process_path(path)

    def _download_by_idx(self, idx):
        self._selected_idx_var = idx
        self.download_tool()

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
            # 优先 Gitee（国内快），再试 GitHub
            for src, label in [(url_bak, "Gitee"), (url, "GitHub")]:
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
            self.after(0, lambda: messagebox.showerror("下载失败", "Gitee 和 GitHub 均无法访问，请检查网络"))

        messagebox.showinfo("开始下载", f"正在下载「{t['name']}」，请稍候...")
        threading.Thread(target=do_download, daemon=True).start()

    def run_tool(self):
        idx = self._selected_idx()
        if idx is None:
            return
        t = self.tools[idx]
        abs_path = resolve_path(t["path"])
        if not os.path.exists(abs_path) and t.get("pan_url"):
            import webbrowser
            webbrowser.open(t["pan_url"])
            return
        # 优先用 launch 字段
        lp = t.get("launch") or t.get("launch_app") or abs_path
        if not os.path.exists(lp):
            lp = abs_path
        launch_tool({"path": lp, "name": t["name"]})

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

    # ── Git 管理页 ────────────────────────────────────

    def _build_git_page(self):
        frame = tk.Frame(self.content, bg=BG)
        self.pages["git"] = frame

        tk.Label(frame, text="🐙  Git 管理", bg=BG, fg=TEXT,
                 font=("微软雅黑", 13, "bold")).pack(anchor="w", padx=16, pady=(12,4))

        # Token 配置区
        cfg_frame = tk.LabelFrame(frame, text="账号 / Token 配置",
                                   bg=BG, fg=ACCENT, font=("微软雅黑",10), padx=12, pady=8)
        cfg_frame.pack(fill="x", padx=16, pady=4)

        self._git_cfg = {}
        self._git_status_labels = {}
        self._git_link_labels = {}  # 存每行的链接label，验证后动态更新
        for label, key, show, link, verify_fn in [
            ("GitHub Token", "github_token", "*",
             "https://github.com/settings/tokens/new",
             lambda v, k="github_token": self._verify_github(v, k)),
            ("Gitee  Token", "gitee_token",  "*",
             "https://gitee.com/profile/personal_access_tokens/new",
             lambda v, k="gitee_token": self._verify_gitee(v, k)),
            ("GitLab Token", "gitlab_token", "*",
             "https://gitlab.com/-/profile/personal_access_tokens",
             lambda v, k="gitlab_token": self._verify_gitlab(v, k)),
            ("GitLab 地址",  "gitlab_url",   "",
             "https://gitlab.com", None),
        ]:
            row = tk.Frame(cfg_frame, bg=BG); row.pack(fill="x", pady=2)
            tk.Label(row, text=label, bg=BG, fg=TEXT,
                     font=("微软雅黑",9), width=14, anchor="w").pack(side="left")
            v = tk.StringVar()
            self._git_cfg[key] = v
            entry = tk.Entry(row, textvariable=v, bg=BG2, fg=TEXT,
                             insertbackground=TEXT, relief="flat",
                             font=("微软雅黑",9), show=show, width=32)
            entry.pack(side="left", padx=6)

            # 状态指示灯
            status_lbl = tk.Label(row, text="⬤", bg=BG, fg=TEXT_DIM,
                                   font=("微软雅黑",10))
            status_lbl.pack(side="left", padx=2)
            if key != "gitlab_url":
                self._git_status_labels[key] = status_lbl

            # 👁 显示/隐藏
            if show == "*":
                eye_btn = tk.Button(row, text="👁", bg=BG, fg=TEXT_DIM,
                                    relief="flat", font=("微软雅黑",9),
                                    cursor="hand2", padx=2)
                eye_btn.pack(side="left")
                def _toggle_show(e=entry, b=eye_btn):
                    if e.cget("show") == "*":
                        e.config(show=""); b.config(fg=ACCENT)
                    else:
                        e.config(show="*"); b.config(fg=TEXT_DIM)
                eye_btn.config(command=_toggle_show)

            # ✓ 验证
            if verify_fn:
                tk.Button(row, text="✓ 验证", bg=BG3, fg=ACCENT2,
                          relief="flat", font=("微软雅黑",9), padx=6,
                          cursor="hand2",
                          command=lambda fn=verify_fn, var=v: fn(var.get().strip())
                          ).pack(side="left", padx=2)

            # 🔗 获取 / 验证后变「我的主页」
            lbl = tk.Label(row, text="🔗 获取", bg=BG, fg=ACCENT,
                           font=("微软雅黑",9,"underline"), cursor="hand2")
            lbl.pack(side="left", padx=4)
            lbl.bind("<Button-1>", lambda e, url=link: __import__("webbrowser").open(url))
            if key != "gitlab_url":
                self._git_link_labels[key] = lbl

        btn_row = tk.Frame(cfg_frame, bg=BG); btn_row.pack(anchor="w", pady=4)
        StyledButton(btn_row, "💾 保存配置", self._save_git_cfg, ACCENT).pack(side="left", padx=4)
        StyledButton(btn_row, "📋 加载配置", self._load_git_cfg).pack(side="left", padx=4)
        self._load_git_cfg()

        # 操作区
        op_frame = tk.Frame(frame, bg=BG); op_frame.pack(fill="x", padx=16, pady=4)

        # 下载项目
        dl_frame = tk.LabelFrame(op_frame, text="⬇ 克隆/下载项目",
                                  bg=BG, fg=ACCENT, font=("微软雅黑",10), padx=12, pady=8)
        dl_frame.pack(side="left", fill="both", expand=True, padx=(0,8))

        tk.Label(dl_frame, text="仓库地址（支持 GitHub/Gitee/GitLab）：",
                 bg=BG, fg=TEXT_DIM, font=("微软雅黑",9)).pack(anchor="w")
        self._clone_url = tk.StringVar()
        tk.Entry(dl_frame, textvariable=self._clone_url, bg=BG2, fg=TEXT,
                 insertbackground=TEXT, relief="flat",
                 font=("微软雅黑",9), width=40).pack(fill="x", pady=4)
        tk.Label(dl_frame, text="保存到：", bg=BG, fg=TEXT_DIM,
                 font=("微软雅黑",9)).pack(anchor="w")
        path_row = tk.Frame(dl_frame, bg=BG); path_row.pack(fill="x", pady=2)
        self._clone_dest = tk.StringVar(value=SCRIPT_DIR)
        tk.Entry(path_row, textvariable=self._clone_dest, bg=BG2, fg=TEXT,
                 insertbackground=TEXT, relief="flat",
                 font=("微软雅黑",9), width=30).pack(side="left", fill="x", expand=True)
        StyledButton(path_row, "📁", lambda: self._clone_dest.set(
            filedialog.askdirectory() or self._clone_dest.get())).pack(side="left", padx=4)
        StyledButton(dl_frame, "⬇ 克隆", self._do_clone, "#89b4fa").pack(anchor="w", pady=4)

        # 上传项目
        up_frame = tk.LabelFrame(op_frame, text="⬆ 上传/推送项目",
                                  bg=BG, fg=ACCENT, font=("微软雅黑",10), padx=12, pady=8)
        up_frame.pack(side="left", fill="both", expand=True)

        tk.Label(up_frame, text="拖拽文件夹/快捷方式到此处，或选择目录：",
                 bg=BG, fg=TEXT_DIM, font=("微软雅黑",9)).pack(anchor="w")

        self._upload_drop = tk.Label(up_frame,
            text="📂  拖拽项目文件夹到这里", bg=BG3, fg=TEXT_DIM,
            font=("微软雅黑",10), pady=20, relief="flat", cursor="hand2")
        self._upload_drop.pack(fill="x", pady=4)
        if _DND_OK:
            self._upload_drop.drop_target_register(DND_FILES)
            self._upload_drop.dnd_bind("<<Drop>>", self._on_upload_drop)

        StyledButton(up_frame, "📁 选择目录", self._pick_upload_dir).pack(anchor="w", pady=2)

        tk.Label(up_frame, text="目标仓库地址（留空则推送到已有remote）：",
                 bg=BG, fg=TEXT_DIM, font=("微软雅黑",9)).pack(anchor="w", pady=(6,0))
        self._upload_remote = tk.StringVar()
        tk.Entry(up_frame, textvariable=self._upload_remote, bg=BG2, fg=TEXT,
                 insertbackground=TEXT, relief="flat",
                 font=("微软雅黑",9), width=36).pack(fill="x", pady=2)
        StyledButton(up_frame, "⬆ 推送", self._do_push, ACCENT2).pack(anchor="w", pady=4)

        # 日志
        self._git_log = tk.Text(frame, bg=BG2, fg=TEXT, font=("Consolas",9),
                                 relief="flat", state="disabled", height=8)
        self._git_log.pack(fill="both", expand=True, padx=16, pady=4)

    def _git_log_append(self, msg):
        self._git_log.config(state="normal")
        self._git_log.insert("end", msg + "\n")
        self._git_log.see("end")
        self._git_log.config(state="disabled")

    def _set_git_status(self, key, ok, profile_url=""):
        lbl = self._git_status_labels.get(key)
        if lbl:
            lbl.config(fg=ACCENT2 if ok else DANGER)
        # 验证成功后把「获取」链接改成「我的主页」
        link_lbl = self._git_link_labels.get(key)
        if link_lbl and ok and profile_url:
            link_lbl.config(text="👤 我的主页", fg=ACCENT2)
            link_lbl.bind("<Button-1>",
                          lambda e, url=profile_url: __import__("webbrowser").open(url))

    def _verify_github(self, token, key="github_token"):
        if not token:
            messagebox.showwarning("提示", "请先输入 GitHub Token"); return
        import urllib.request, urllib.error
        try:
            req = urllib.request.Request(
                "https://api.github.com/user",
                headers={"Authorization": f"token {token}", "User-Agent": "KHY-Tools"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read())
            login = data.get('login', '')
            profile_url = f"https://github.com/{login}"
            self._set_git_status(key, True, profile_url)
            messagebox.showinfo("✓ GitHub 验证成功",
                f"用户名：{login}\n邮箱：{data.get('email') or '未公开'}\n仓库数：{data.get('public_repos')}")
        except urllib.error.HTTPError as e:
            self._set_git_status(key, False)
            messagebox.showerror("✗ 验证失败", f"HTTP {e.code}：Token 无效或权限不足")
        except Exception as e:
            self._set_git_status(key, False)
            messagebox.showerror("✗ 验证失败", f"网络错误：{e}")

    def _verify_gitee(self, token, key="gitee_token"):
        if not token:
            messagebox.showwarning("提示", "请先输入 Gitee Token"); return
        import urllib.request, urllib.error
        try:
            with urllib.request.urlopen(
                    f"https://gitee.com/api/v5/user?access_token={token}", timeout=8) as r:
                data = json.loads(r.read())
            login = data.get('login', '')
            profile_url = f"https://gitee.com/{login}"
            self._set_git_status(key, True, profile_url)
            messagebox.showinfo("✓ Gitee 验证成功",
                f"用户名：{login}\n昵称：{data.get('name')}\n邮箱：{data.get('email') or '未公开'}")
        except urllib.error.HTTPError as e:
            self._set_git_status(key, False)
            messagebox.showerror("✗ 验证失败", f"HTTP {e.code}：Token 无效或已过期")
        except Exception as e:
            self._set_git_status(key, False)
            messagebox.showerror("✗ 验证失败", f"网络错误：{e}")

    def _verify_gitlab(self, token, key="gitlab_token"):
        if not token:
            messagebox.showwarning("提示", "请先输入 GitLab Token"); return
        base = self._git_cfg.get("gitlab_url", tk.StringVar()).get().strip() or "https://gitlab.com"
        import urllib.request, urllib.error
        try:
            req = urllib.request.Request(
                f"{base.rstrip('/')}/api/v4/user",
                headers={"PRIVATE-TOKEN": token})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read())
            username = data.get('username', '')
            profile_url = f"{base.rstrip('/')}/{username}"
            self._set_git_status(key, True, profile_url)
            messagebox.showinfo("✓ GitLab 验证成功",
                f"用户名：{username}\n昵称：{data.get('name')}\n邮箱：{data.get('email') or '未公开'}")
        except urllib.error.HTTPError as e:
            self._set_git_status(key, False)
            messagebox.showerror("✗ 验证失败", f"HTTP {e.code}：Token 无效或地址错误")
        except Exception as e:
            self._set_git_status(key, False)
            messagebox.showerror("✗ 验证失败", f"网络错误：{e}")

    def _save_git_cfg(self):
        cfg = {k: v.get().strip() for k, v in self._git_cfg.items()}
        with open(GIT_CONFIG_JSON, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        self._git_log_append("✓ 配置已保存")

    def _load_git_cfg(self):
        if os.path.exists(GIT_CONFIG_JSON):
            with open(GIT_CONFIG_JSON, encoding="utf-8") as f:
                cfg = json.load(f)
            for k, v in self._git_cfg.items():
                v.set(cfg.get(k, ""))

    def _find_git(self):
        for g in ["git", r"D:\Program Files\Git\cmd\git.exe",
                  r"C:\Program Files\Git\cmd\git.exe"]:
            try:
                if subprocess.run([g, "--version"], capture_output=True, timeout=3).returncode == 0:
                    return g
            except Exception:
                pass
        return None

    def _do_clone(self):
        url = self._clone_url.get().strip()
        dest = self._clone_dest.get().strip()
        if not url:
            messagebox.showwarning("提示", "请输入仓库地址")
            return
        git = self._find_git()
        if not git:
            messagebox.showerror("错误", "未找到 git，请先安装 Git")
            return

        # 注入 token 到 URL
        url_with_token = self._inject_token(url)
        repo_name = url.rstrip("/").split("/")[-1].replace(".git", "")
        clone_to = os.path.join(dest, repo_name)

        self._git_log_append(f"⬇ 克隆 {url} → {clone_to}")
        import threading
        def do():
            r = subprocess.run([git, "clone", url_with_token, clone_to],
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            if r.returncode == 0:
                self.after(0, lambda: self._git_log_append(f"✓ 克隆成功：{clone_to}"))
                # 询问是否加入工具管理
                self.after(0, lambda: self._ask_add_to_tools(clone_to, repo_name))
            else:
                err = r.stderr or r.stdout
                self.after(0, lambda: self._git_log_append(f"✗ 克隆失败：{err[:200]}"))
        threading.Thread(target=do, daemon=True).start()

    def _inject_token(self, url):
        """把 token 注入到 HTTPS URL 里"""
        cfg = {k: v.get().strip() for k, v in self._git_cfg.items()}
        if "github.com" in url and cfg.get("github_token"):
            return url.replace("https://", f"https://{cfg['github_token']}@")
        if "gitee.com" in url and cfg.get("gitee_token"):
            return url.replace("https://", f"https://{cfg['gitee_token']}@")
        gitlab_url = cfg.get("gitlab_url", "")
        if gitlab_url and gitlab_url in url and cfg.get("gitlab_token"):
            return url.replace("https://", f"https://oauth2:{cfg['gitlab_token']}@")
        return url

    def _ask_add_to_tools(self, path, name):
        if messagebox.askyesno("加入工具管理", f"是否将「{name}」加入工具管理列表？"):
            self._process_path(path)

    def _on_upload_drop(self, event):
        raw = event.data.strip()
        paths = []
        if raw.startswith("{"):
            import re
            paths = [a or b for a, b in re.findall(r'\{([^}]+)\}|(\S+)', raw)]
        else:
            paths = raw.split()
        for p in paths:
            p = p.strip().strip('"')
            if p:
                self._prepare_upload(p)

    def _pick_upload_dir(self):
        p = filedialog.askdirectory(title="选择要上传的项目目录")
        if p:
            self._prepare_upload(p)

    def _prepare_upload(self, path):
        # 如果是快捷方式，询问是否上传整个项目
        if path.lower().endswith(".lnk"):
            target = self._resolve_lnk(path)
            if target and os.path.isfile(target):
                proj_dir = os.path.dirname(target)
                ans = messagebox.askyesnocancel(
                    "上传整个项目？",
                    f"快捷方式指向：{target}\n\n"
                    f"是 → 上传整个项目目录：{proj_dir}\n"
                    f"否 → 只上传此文件")
                if ans is None: return
                path = proj_dir if ans else target
            elif target:
                path = target

        self._upload_drop.config(text=f"📂 {os.path.basename(path)}")
        remote = self._upload_remote.get().strip()
        self._do_push_path(path, remote)

    def _do_push(self):
        # 从 drop 区域取当前路径
        txt = self._upload_drop.cget("text")
        if txt.startswith("📂  拖拽"):
            messagebox.showwarning("提示", "请先拖拽或选择要上传的项目目录")
            return
        # 重新触发（用户可能改了 remote）
        messagebox.showinfo("提示", "请重新拖拽或选择目录以推送")

    def _do_push_path(self, path, remote_url=""):
        git = self._find_git()
        if not git:
            messagebox.showerror("错误", "未找到 git")
            return
        import threading
        def do():
            # 如果目录没有 .git，先 init
            git_dir = os.path.join(path, ".git")
            if not os.path.exists(git_dir):
                subprocess.run([git, "-C", path, "init"], capture_output=True)
                self.after(0, lambda: self._git_log_append("✓ git init 完成"))

            # 设置 remote
            if remote_url:
                url_with_token = self._inject_token(remote_url)
                r = subprocess.run([git, "-C", path, "remote", "get-url", "origin"],
                                   capture_output=True)
                if r.returncode != 0:
                    subprocess.run([git, "-C", path, "remote", "add", "origin",
                                    url_with_token], capture_output=True)
                else:
                    subprocess.run([git, "-C", path, "remote", "set-url", "origin",
                                    url_with_token], capture_output=True)

            # add + commit + push
            subprocess.run([git, "-C", path, "add", "-A"], capture_output=True)
            r = subprocess.run([git, "-C", path, "commit", "-m", "上传项目"],
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            if "nothing to commit" in (r.stdout + r.stderr):
                self.after(0, lambda: self._git_log_append("ℹ 无变更，直接推送"))

            r = subprocess.run([git, "-C", path, "push", "-u", "origin", "main",
                                 "--force"],
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            if r.returncode == 0:
                self.after(0, lambda: self._git_log_append("✓ 推送成功"))
            else:
                err = r.stderr or r.stdout
                self.after(0, lambda: self._git_log_append(f"✗ 推送失败：{err[:300]}"))
        threading.Thread(target=do, daemon=True).start()
        self._git_log_append(f"⬆ 推送 {path} ...")

    # ── 文件清理页 ────────────────────────────────────

    def _build_clean_page(self):
        frame = tk.Frame(self.content, bg=BG)
        self.pages["clean"] = frame

        bar = tk.Frame(frame, bg=BG, pady=8); bar.pack(fill="x", padx=16)
        tk.Label(bar, text="🗂  文件清理 & C盘管理", bg=BG, fg=TEXT,
                 font=("微软雅黑", 13, "bold")).pack(side="left")

        # 快速清理按钮
        quick = tk.Frame(frame, bg=BG); quick.pack(fill="x", padx=16, pady=4)
        for txt, mode in [("🗑 临时文件","temp"),("⬇ 未完成下载","dl"),
                          ("📁 空文件夹","empty")]:
            StyledButton(quick, txt, lambda m=mode: self._clean(m)).pack(side="left", padx=4)
        StyledButton(quick, "🖥 整理桌面",
                     lambda: self._run_script("desktop_organizer.py")).pack(side="left", padx=4)

        # C盘扫描区
        scan_frame = tk.LabelFrame(frame, text="C盘占用扫描（安全可清理项）",
                                    bg=BG, fg=ACCENT, font=("微软雅黑",10),
                                    padx=8, pady=6)
        scan_frame.pack(fill="x", padx=16, pady=6)

        scan_btn_row = tk.Frame(scan_frame, bg=BG); scan_btn_row.pack(fill="x")
        self._scan_btn = StyledButton(scan_btn_row, "🔍 扫描C盘可清理项",
                                       self._scan_c_drive, ACCENT)
        self._scan_btn.pack(side="left", padx=4)
        self._scan_del_btn = StyledButton(scan_btn_row, "🗑 删除选中项",
                                           self._delete_selected_scan, DANGER)
        self._scan_del_btn.pack(side="left", padx=4)
        self._scan_size_lbl = tk.Label(scan_btn_row, text="", bg=BG, fg=ACCENT2,
                                        font=("微软雅黑",9))
        self._scan_size_lbl.pack(side="left", padx=8)

        # 扫描结果列表
        cols = ("类型", "路径", "大小", "说明")
        style = ttk.Style()
        style.configure("Scan.Treeview", background=BG2, foreground=TEXT,
                        fieldbackground=BG2, rowheight=26, font=("微软雅黑",9))
        style.configure("Scan.Treeview.Heading", background=BG3, foreground=ACCENT,
                        font=("微软雅黑",9,"bold"))
        style.map("Scan.Treeview", background=[("selected","#3d3d5c")])

        scan_tree_frame = tk.Frame(scan_frame, bg=BG)
        scan_tree_frame.pack(fill="both", expand=True, pady=4)
        self.scan_tree = ttk.Treeview(scan_tree_frame, columns=cols,
                                       show="headings", style="Scan.Treeview",
                                       selectmode="extended", height=8)
        for col, w in zip(cols, [100, 320, 80, 180]):
            self.scan_tree.heading(col, text=col)
            self.scan_tree.column(col, width=w, minwidth=40)
        scan_sb = ttk.Scrollbar(scan_tree_frame, orient="vertical",
                                 command=self.scan_tree.yview)
        self.scan_tree.configure(yscrollcommand=scan_sb.set)
        self.scan_tree.pack(side="left", fill="both", expand=True)
        scan_sb.pack(side="right", fill="y")

        # 日志
        self.clean_log = tk.Text(frame, bg=BG2, fg=TEXT, font=("Consolas",9),
                                  relief="flat", state="disabled", height=6)
        self.clean_log.pack(fill="x", padx=16, pady=4)
        self.clean_log.tag_config("ok",  foreground=ACCENT2)
        self.clean_log.tag_config("err", foreground=DANGER)

    def _scan_c_drive(self):
        """扫描C盘所有非系统目录，找出可安全清理的项目"""
        self.scan_tree.delete(*self.scan_tree.get_children())
        self._scan_size_lbl.config(text="扫描中，请稍候...")
        self._scan_btn.config(state="disabled")

        def do():
            results = []  # (type, path, size_bytes, desc)

            def fmt_size(b):
                if b > 1024**3: return f"{b/1024**3:.1f} GB"
                if b > 1024**2: return f"{b/1024**2:.0f} MB"
                return f"{b/1024:.0f} KB"

            def dir_size(path):
                total = 0
                try:
                    for dp, _, fns in os.walk(path):
                        for f in fns:
                            try: total += os.path.getsize(os.path.join(dp, f))
                            except Exception: pass
                except PermissionError:
                    pass
                return total

            # ── 1. 已知可清理目录（精确匹配）──────────
            known = [
                (os.path.expandvars(r"%TEMP%"),
                 "系统临时", "Windows 临时文件"),
                (r"C:\Windows\Temp",
                 "系统临时", "Windows 系统临时"),
                (r"C:\Windows\SoftwareDistribution\Download",
                 "更新缓存", "Windows Update 下载缓存"),
                (os.path.expandvars(r"%LOCALAPPDATA%\pip\cache"),
                 "pip缓存", "Python pip 缓存"),
                (os.path.expandvars(r"%APPDATA%\npm-cache"),
                 "npm缓存", "npm 包缓存"),
                (os.path.expandvars(r"%LOCALAPPDATA%\npm-cache"),
                 "npm缓存", "npm 包缓存"),
                (os.path.expandvars(r"%LOCALAPPDATA%\Yarn\Cache"),
                 "yarn缓存", "yarn 包缓存"),
                (os.path.expandvars(r"%LOCALAPPDATA%\pnpm\store"),
                 "pnpm缓存", "pnpm 包存储"),
                (os.path.expandvars(r"%LOCALAPPDATA%\pyinstaller"),
                 "PyInstaller缓存", "PyInstaller 构建缓存"),
                (os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache"),
                 "Chrome缓存", "Chrome 浏览器缓存"),
                (os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cache"),
                 "Edge缓存", "Edge 浏览器缓存"),
                (os.path.expandvars(r"%USERPROFILE%\.ollama\models"),
                 "Ollama模型", "本地AI模型（删除需重新下载）"),
                (os.path.expandvars(r"%USERPROFILE%\.cache"),
                 "用户缓存", "各类工具缓存目录"),
                (os.path.expandvars(r"%LOCALAPPDATA%\Temp"),
                 "本地临时", "LocalAppData 临时文件"),
            ]
            for path, type_name, desc in known:
                if not os.path.exists(path): continue
                size = dir_size(path)
                if size > 1024 * 1024:
                    results.append((type_name, path, size, desc))

            # ── 2. 扫描 C 盘根目录下的非系统文件夹 ──
            WIN11_SYSTEM_DIRS = {
                "windows", "program files", "program files (x86)",
                "programdata", "users", "recovery", "$recycle.bin",
                "system volume information", "perflogs",
                "msocache", "boot", "$windows.~bt", "$windows.~ws",
            }
            try:
                for name in os.listdir("C:\\"):
                    if name.lower() in WIN11_SYSTEM_DIRS:
                        continue
                    full = os.path.join("C:\\", name)
                    if not os.path.isdir(full):
                        continue
                    size = dir_size(full)
                    if size > 1024 * 1024:
                        results.append(("C盘自定义目录", full, size,
                                         "非系统目录，可检查是否需要"))
            except PermissionError:
                pass

            # ── 3. 扫描用户目录下的 node_modules ──
            user_dir = os.path.expanduser("~")
            for root, dirs, _ in os.walk(user_dir):
                depth = root.replace(user_dir, "").count(os.sep)
                if depth > 5:
                    dirs.clear(); continue
                # 跳过已知系统目录
                dirs[:] = [d for d in dirs if d.lower() not in
                           {"appdata", ".git", "windows", "system32"}]
                if "node_modules" in dirs:
                    nm = os.path.join(root, "node_modules")
                    size = dir_size(nm)
                    if size > 1024 * 1024:
                        results.append(("node_modules", nm, size,
                                         "Node依赖包，可删除后npm install恢复"))
                    dirs.remove("node_modules")

            # ── 4. 扫描 Program Files 下的卸载残留 ──
            for pf in [r"C:\Program Files", r"C:\Program Files (x86)"]:
                if not os.path.exists(pf): continue
                try:
                    for name in os.listdir(pf):
                        full = os.path.join(pf, name)
                        if not os.path.isdir(full): continue
                        size = dir_size(full)
                        if 0 < size < 1024 * 1024:  # <1MB 可能是残留
                            results.append(("⚠ 安装残留?", full, size,
                                             "很小的目录，可能是卸载残留"))
                        # 大型软件不再列入（避免误删）
                except PermissionError:
                    pass

            # 去重 + 按大小排序
            seen = set()
            unique = []
            for item in results:
                key = item[1].lower()
                if key not in seen:
                    seen.add(key)
                    unique.append(item)
            unique.sort(key=lambda x: x[2], reverse=True)

            total = sum(r[2] for r in unique)

            self.after(0, lambda: [
                self.scan_tree.delete(*self.scan_tree.get_children()),
                [self.scan_tree.insert("", "end",
                    values=(t, p, fmt_size(s), d),
                    tags=("safe",) if any(k in t for k in ("缓存","临时","残留","node_modules")) else ("info",))
                 for t, p, s, d in unique],
                self.scan_tree.tag_configure("safe", foreground=ACCENT2),
                self.scan_tree.tag_configure("info", foreground=TEXT_DIM),
                self._scan_size_lbl.config(
                    text=f"共 {len(unique)} 项，合计 {fmt_size(total)}  |  绿色=可安全清理  灰色=仅供参考"),
                self._scan_btn.config(state="normal"),
                self._log(f"✓ 扫描完成，{len(unique)} 项，共 {fmt_size(total)}", "ok")
            ])

        threading.Thread(target=do, daemon=True).start()

    def _delete_selected_scan(self):
        sel = self.scan_tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择要删除的项目")
            return
        paths = [self.scan_tree.item(s)["values"][1] for s in sel]
        names = [self.scan_tree.item(s)["values"][0] for s in sel]
        if not messagebox.askyesno("确认删除",
                f"确定删除以下 {len(paths)} 项？\n" +
                "\n".join(f"  • {n}: {p[:50]}" for n,p in zip(names,paths)) +
                "\n\n⚠ 删除后无法恢复！"):
            return
        import shutil
        deleted = 0
        for path in paths:
            try:
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                deleted += 1
                self._log(f"✓ 已删除：{path}", "ok")
            except Exception as e:
                self._log(f"✗ 删除失败：{path} ({e})", "err")
        for s in sel:
            self.scan_tree.delete(s)
        self._log(f"完成，删除 {deleted}/{len(paths)} 项")

    def _log(self, msg, tag=""):
        self.clean_log.config(state="normal")
        self.clean_log.insert("end", msg + "\n", tag)
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
        import datetime
        self.bak_tree.delete(*self.bak_tree.get_children())
        self.backup_records = []

        cfg = os.path.join(SCRIPT_DIR, "backup_dir.txt")
        base = ""
        if os.path.exists(cfg):
            with open(cfg) as f:
                base = f.read().strip()

        type_labels = {
            "system": "完整系统", "conly": "系统盘",
            "pdf": "PDF文件", "word": "Word文档",
            "wbadmin": "系统镜像(wbAdmin)"
        }

        entries = []  # (sort_key, name, label, time_str, size_str, path, btype)

        # ── 1. 扫描我们自己创建的备份（type_YYYYMMDD_HHMMSS 格式）──
        if base and os.path.isdir(base):
            for name in os.listdir(base):
                path = os.path.join(base, name)
                parts = name.split("_")
                if len(parts) < 3:
                    continue
                btype = parts[0]
                if btype not in ("system", "conly", "pdf", "word"):
                    continue
                label = type_labels.get(btype, btype)
                try:
                    ts = "_".join(parts[1:3])
                    dt = datetime.datetime.strptime(ts, "%Y%m%d_%H%M%S")
                    time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                    sort_key = dt
                except Exception:
                    time_str = "未知时间"
                    sort_key = datetime.datetime.min
                size_str = self._calc_size(path)
                entries.append((sort_key, name, label, time_str, size_str, path, btype))

        # ── 2. 扫描 wbAdmin 系统镜像备份（WindowsImageBackup 目录）──
        # 结构：WindowsImageBackup\<计算机名>\  （里面有 Backup xxx / Catalog / Logs 等）
        # 整个 <计算机名> 文件夹 = 一次完整备份，合并为一条记录
        import string
        search_roots = set()
        if base:
            drive = os.path.splitdrive(base)[0]
            if drive:
                search_roots.add(drive + "\\")
        for letter in string.ascii_uppercase:
            d = letter + ":\\"
            if os.path.isdir(d):
                search_roots.add(d)

        for root in search_roots:
            wib = os.path.join(root, "WindowsImageBackup")
            if not os.path.isdir(wib):
                continue
            try:
                pc_names = os.listdir(wib)
            except PermissionError:
                continue
            for pc_name in pc_names:
                pc_path = os.path.join(wib, pc_name)
                if not os.path.isdir(pc_path):
                    continue
                label = type_labels["wbadmin"]
                sort_key = datetime.datetime.min
                time_str = "未知时间"
                try:
                    sub_items = os.listdir(pc_path)
                except PermissionError:
                    sub_items = []
                for sub in sub_items:
                    if not sub.startswith("Backup "):
                        continue
                    try:
                        parts2 = sub.split(" ")
                        dt = datetime.datetime.strptime(
                            f"{parts2[1]} {parts2[2]}", "%Y-%m-%d %H%M%S")
                        if sort_key == datetime.datetime.min or dt < sort_key:
                            sort_key = dt
                            time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        pass
                if sort_key == datetime.datetime.min:
                    try:
                        mtime = os.path.getmtime(pc_path)
                        sort_key = datetime.datetime.fromtimestamp(mtime)
                        time_str = sort_key.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        pass
                display_name = f"[系统镜像] {pc_name}"
                size_str = self._calc_size(pc_path)
                entries.append((sort_key, display_name, label, time_str,
                                size_str, pc_path, "wbadmin"))

        # 按时间倒序排列
        entries.sort(key=lambda x: x[0], reverse=True)

        for sort_key, name, label, time_str, size_str, path, btype in entries:
            self.backup_records.append({"name": name, "path": path, "type": btype})
            self.bak_tree.insert("", "end", values=(name, label, time_str, size_str, path))

    def _calc_size(self, path):
        try:
            if os.path.isdir(path):
                size = sum(os.path.getsize(os.path.join(r, f))
                           for r, _, fs in os.walk(path) for f in fs)
            else:
                size = os.path.getsize(path)
            if size >= 1024 ** 3:
                return f"{size/1024**3:.1f} GB"
            return f"{size/1024**2:.1f} MB"
        except Exception:
            return "-"

    def _get_path_size_mb(self, path):
        """返回文件或目录的大小（MB），快速估算，目录超过限制时提前返回"""
        LIMIT = 50 * 1024 * 1024  # 50MB，超过就不继续算了
        try:
            if os.path.isfile(path):
                return os.path.getsize(path) / 1024 / 1024
            total = 0
            for r, _, files in os.walk(path):
                for f in files:
                    try:
                        total += os.path.getsize(os.path.join(r, f))
                    except Exception:
                        pass
                    if total > LIMIT * 20:  # 超过1GB直接返回
                        return total / 1024 / 1024
            return total / 1024 / 1024
        except Exception:
            return 0

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

        if btype in ("system", "conly", "wbadmin"):
            messagebox.showinfo("系统还原说明",
                "系统镜像还原步骤：\n\n"
                "【方法一】系统可以正常启动时：\n"
                "  控制面板 → 备份和还原(Windows 7)\n"
                "  → 恢复系统设置或计算机\n\n"
                "【方法二】系统崩溃无法启动时：\n"
                "  1. 用 Windows 安装U盘启动\n"
                "  2. 选择「修复计算机」\n"
                "  3. 疑难解答 → 高级选项\n"
                "  4. 系统映像恢复\n\n"
                f"备份位置：\n{rec['path']}")
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
