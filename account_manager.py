#!/usr/bin/env python3
"""
账号管理工具
- 任意软件账号存储（AES加密）
- 一键启动对应应用
- 自定义平台/软件名
依赖：pip install cryptography
"""
import os, sys, json, subprocess, base64, threading, glob
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_USER_DATA  = os.path.join(os.environ.get("APPDATA", SCRIPT_DIR), "KHY小工具")
os.makedirs(_USER_DATA, exist_ok=True)
ACCOUNTS_FILE = os.path.join(_USER_DATA, "accounts.enc")
KEY_FILE      = os.path.join(_USER_DATA, "accounts.key")

BG="#1e1e2e"; BG2="#2a2a3e"; BG3="#313145"
ACCENT="#7c9ef8"; ACCENT2="#a6e3a1"; DANGER="#f38ba8"
TEXT="#cdd6f4"; TEXT_DIM="#6c7086"; BTN="#45475a"

# ══════════════════════════════════════════════════════
# 加密/解密
# ══════════════════════════════════════════════════════
def _get_or_create_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f: return f.read()
    key = os.urandom(16)
    with open(KEY_FILE, "wb") as f: f.write(key)
    return key

def _encrypt(data: str) -> bytes:
    try:
        from cryptography.fernet import Fernet
        k = base64.urlsafe_b64encode(_get_or_create_key() + b"\x00"*16)[:44] + b"="
        return Fernet(k).encrypt(data.encode())
    except ImportError:
        return base64.b64encode(data.encode())

def _decrypt(data: bytes) -> str:
    try:
        from cryptography.fernet import Fernet
        k = base64.urlsafe_b64encode(_get_or_create_key() + b"\x00"*16)[:44] + b"="
        return Fernet(k).decrypt(data).decode()
    except ImportError:
        return base64.b64decode(data).decode()

def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE): return []
    try:
        with open(ACCOUNTS_FILE, "rb") as f: return json.loads(_decrypt(f.read()))
    except Exception: return []

def save_accounts(accounts):
    with open(ACCOUNTS_FILE, "wb") as f: f.write(_encrypt(json.dumps(accounts, ensure_ascii=False)))

# ══════════════════════════════════════════════════════
# 扫描已安装应用
# ══════════════════════════════════════════════════════
def scan_installed_apps():
    """扫描开始菜单和桌面，返回 [(显示名, 路径)]"""
    results = []
    seen = set()
    search_dirs = [
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu"),
        os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu"),
        os.path.expandvars(r"%USERPROFILE%\Desktop"),
        r"C:\Users\Public\Desktop",
    ]
    for d in search_dirs:
        if not os.path.exists(d): continue
        for fpath in glob.glob(os.path.join(d, "**", "*.lnk"), recursive=True):
            name = os.path.splitext(os.path.basename(fpath))[0]
            key  = name.lower()
            if key not in seen:
                seen.add(key)
                results.append((name, fpath))
    results.sort(key=lambda x: x[0].lower())
    return results

# ══════════════════════════════════════════════════════
# 主界面
# ══════════════════════════════════════════════════════
class AccountManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("账号管理工具")
        self.geometry("900x580")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.accounts = load_accounts()
        self._selected = None
        self._installed_apps = []  # 缓存已安装应用列表
        self._build_ui()
        self._refresh()
        # 后台扫描已安装应用
        threading.Thread(target=self._scan_apps_bg, daemon=True).start()

    def _scan_apps_bg(self):
        self._installed_apps = scan_installed_apps()

    def _build_ui(self):
        top = tk.Frame(self, bg=BG2, pady=10); top.pack(fill="x")
        tk.Label(top, text="🔑  账号管理工具", bg=BG2, fg=ACCENT,
                 font=("微软雅黑",14,"bold")).pack(side="left", padx=20)
        tk.Label(top, text="密码已加密存储，仅保存在本机",
                 bg=BG2, fg=TEXT_DIM, font=("微软雅黑",9)).pack(side="right", padx=20)

        # 搜索栏
        bar = tk.Frame(self, bg=BG, pady=6); bar.pack(fill="x", padx=16)
        tk.Label(bar, text="搜索：", bg=BG, fg=TEXT, font=("微软雅黑",10)).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh())
        tk.Entry(bar, textvariable=self.search_var, bg=BG2, fg=TEXT,
                 insertbackground=TEXT, relief="flat",
                 font=("微软雅黑",10), width=20).pack(side="left", padx=6, ipady=4)

        for txt, color, cmd in [
            ("＋ 添加账号", ACCENT,  self._add_account),
            ("✎ 编辑",      BTN,     self._edit_account),
            ("✕ 删除",      DANGER,  self._delete_account),
            ("📋 复制密码",  BTN,     self._copy_password),
            ("▶ 启动应用",  ACCENT2, self._launch_app),
        ]:
            tk.Button(bar, text=txt,
                      bg=color, fg=BG if color not in (BTN,) else TEXT,
                      relief="flat", font=("微软雅黑",10), padx=10, pady=5,
                      cursor="hand2", command=cmd).pack(side="left", padx=3)

        # 列表
        cols = ("软件/平台", "账号", "备注", "应用", "上次使用")
        style = ttk.Style(); style.theme_use("clam")
        style.configure("Acc.Treeview", background=BG2, foreground=TEXT,
                        fieldbackground=BG2, rowheight=34, font=("微软雅黑",10))
        style.configure("Acc.Treeview.Heading", background=BG3, foreground=ACCENT,
                        font=("微软雅黑",10,"bold"))
        style.map("Acc.Treeview", background=[("selected","#3d3d5c")],
                  foreground=[("selected",ACCENT)])

        tf = tk.Frame(self, bg=BG); tf.pack(fill="both", expand=True, padx=16, pady=4)
        self.tree = ttk.Treeview(tf, columns=cols, show="headings", style="Acc.Treeview")
        for col, w in zip(cols, [130,160,160,200,90]):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, minwidth=60)
        sb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", lambda e: self._launch_app())

        self.status = tk.Label(self, text="", bg=BG, fg=TEXT_DIM,
                                font=("微软雅黑",9), anchor="w")
        self.status.pack(fill="x", padx=16, pady=4)

    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        kw = self.search_var.get().lower()
        for i, acc in enumerate(self.accounts):
            if kw and not any(kw in str(acc.get(k,"")).lower()
                              for k in ("platform","username","note")):
                continue
            app_name = os.path.splitext(os.path.basename(
                acc.get("app_path","")))[0] or "未设置"
            self.tree.insert("", "end", iid=str(i), values=(
                acc.get("platform",""),
                acc.get("username",""),
                acc.get("note",""),
                app_name,
                acc.get("last_used","从未"),
            ))
        self.status.config(text=f"共 {len(self.accounts)} 个账号")

    def _on_select(self, e=None):
        sel = self.tree.selection()
        self._selected = int(sel[0]) if sel else None

    def _selected_account(self):
        if self._selected is None:
            messagebox.showwarning("提示", "请先选择一个账号"); return None
        return self.accounts[self._selected]

    # ── 添加/编辑对话框 ───────────────────────────
    def _add_account(self):  self._open_dialog()
    def _edit_account(self):
        acc = self._selected_account()
        if acc: self._open_dialog(acc, self._selected)

    def _open_dialog(self, acc=None, idx=None):
        win = tk.Toplevel(self)
        win.title("添加账号" if acc is None else "编辑账号")
        win.geometry("520x440"); win.configure(bg=BG)
        win.resizable(False, False); win.grab_set()
        d = acc or {}
        fields = {}

        def lrow(label, key, show="", hint=""):
            r = tk.Frame(win, bg=BG); r.pack(fill="x", padx=24, pady=5)
            tk.Label(r, text=label, bg=BG, fg=TEXT, font=("微软雅黑",10),
                     width=10, anchor="w").pack(side="left")
            v = tk.StringVar(value=d.get(key,""))
            e = tk.Entry(r, textvariable=v, bg=BG2, fg=TEXT, insertbackground=TEXT,
                         relief="flat", font=("微软雅黑",10), show=show, width=30)
            e.pack(side="left", padx=6, ipady=5)
            if hint:
                tk.Label(r, text=hint, bg=BG, fg=TEXT_DIM,
                         font=("微软雅黑",8)).pack(side="left")
            fields[key] = (v, e)
            return v, e

        tk.Label(win, text="软件/平台名称：", bg=BG, fg=TEXT,
                 font=("微软雅黑",10)).pack(anchor="w", padx=24, pady=(16,0))

        # 平台名：可手动输入，也可从已安装应用选
        plat_row = tk.Frame(win, bg=BG); plat_row.pack(fill="x", padx=24, pady=5)
        tk.Label(plat_row, text="软件名：", bg=BG, fg=TEXT,
                 font=("微软雅黑",10), width=10, anchor="w").pack(side="left")
        plat_var = tk.StringVar(value=d.get("platform",""))
        plat_entry = tk.Entry(plat_row, textvariable=plat_var, bg=BG2, fg=TEXT,
                              insertbackground=TEXT, relief="flat",
                              font=("微软雅黑",10), width=20)
        plat_entry.pack(side="left", padx=6, ipady=5)
        fields["platform"] = (plat_var, plat_entry)

        # 从已安装应用选择
        app_path_var = tk.StringVar(value=d.get("app_path",""))
        def pick_from_installed():
            apps = self._installed_apps
            if not apps:
                apps = scan_installed_apps()
                self._installed_apps = apps
            if not apps:
                messagebox.showinfo("提示", "未找到已安装应用", parent=win); return
            sel_win = tk.Toplevel(win)
            sel_win.title("选择应用"); sel_win.geometry("400x480")
            sel_win.configure(bg=BG); sel_win.grab_set()
            tk.Label(sel_win, text="搜索：", bg=BG, fg=TEXT,
                     font=("微软雅黑",10)).pack(anchor="w", padx=12, pady=(8,0))
            sv = tk.StringVar()
            tk.Entry(sel_win, textvariable=sv, bg=BG2, fg=TEXT,
                     insertbackground=TEXT, relief="flat",
                     font=("微软雅黑",10)).pack(fill="x", padx=12, ipady=4)
            lb = tk.Listbox(sel_win, bg=BG2, fg=TEXT, font=("微软雅黑",10),
                            selectbackground="#3d3d5c", relief="flat")
            lb.pack(fill="both", expand=True, padx=12, pady=6)
            def _fill(kw=""):
                lb.delete(0, "end")
                for name, path in apps:
                    if kw.lower() in name.lower():
                        lb.insert("end", name)
            _fill()
            sv.trace_add("write", lambda *_: _fill(sv.get()))
            def confirm():
                sel = lb.curselection()
                if not sel: return
                name = lb.get(sel[0])
                path = next(p for n,p in apps if n==name)
                plat_var.set(name)
                app_path_var.set(path)
                sel_win.destroy()
            tk.Button(sel_win, text="✓ 选择", bg=ACCENT, fg=BG, relief="flat",
                      font=("微软雅黑",10), padx=16, pady=6, cursor="hand2",
                      command=confirm).pack(pady=6)
            lb.bind("<Double-1>", lambda e: confirm())

        tk.Button(plat_row, text="📱 从已安装应用选择", bg=BG3, fg=TEXT,
                  relief="flat", font=("微软雅黑",9), padx=8, cursor="hand2",
                  command=pick_from_installed).pack(side="left", padx=4)

        uv, _ = lrow("账号",   "username")
        pv, pe = lrow("密码",  "password", show="*")

        # 显示/隐藏密码
        def toggle(): pe.config(show="" if pe.cget("show")=="*" else "*")
        tk.Button(win, text="👁 显示/隐藏密码", bg=BG3, fg=TEXT_DIM,
                  relief="flat", font=("微软雅黑",9), cursor="hand2",
                  command=toggle).pack(anchor="w", padx=80, pady=0)

        lrow("备注", "note", hint="（可选）")

        # 应用路径
        ar = tk.Frame(win, bg=BG); ar.pack(fill="x", padx=24, pady=5)
        tk.Label(ar, text="应用路径：", bg=BG, fg=TEXT, font=("微软雅黑",10),
                 width=10, anchor="w").pack(side="left")
        tk.Entry(ar, textvariable=app_path_var, bg=BG2, fg=TEXT,
                 insertbackground=TEXT, relief="flat",
                 font=("微软雅黑",9), width=28).pack(side="left", padx=6, ipady=4)
        tk.Button(ar, text="📁", bg=BG3, fg=TEXT, relief="flat", cursor="hand2",
                  command=lambda: app_path_var.set(
                      filedialog.askopenfilename(
                          filetypes=[("应用","*.exe *.lnk"),("所有","*.*")]
                      ) or app_path_var.get())).pack(side="left")

        def save():
            data = {k: v.get().strip() for k,(v,_) in fields.items()}
            data["app_path"] = app_path_var.get().strip()
            if not data.get("username"):
                messagebox.showwarning("提示","账号不能为空",parent=win); return
            data["last_used"] = d.get("last_used","从未")
            if idx is not None: self.accounts[idx] = data
            else: self.accounts.append(data)
            save_accounts(self.accounts)
            self._refresh(); win.destroy()

        tk.Button(win, text="💾 保存", bg=ACCENT, fg=BG, relief="flat",
                  font=("微软雅黑",11), padx=24, pady=8, cursor="hand2",
                  command=save).pack(pady=10)

    # ── 删除 ──────────────────────────────────────
    def _delete_account(self):
        acc = self._selected_account()
        if not acc: return
        if messagebox.askyesno("确认", f"删除「{acc.get('username')}」？"):
            self.accounts.pop(self._selected)
            save_accounts(self.accounts)
            self._selected = None; self._refresh()

    # ── 复制密码 ──────────────────────────────────
    def _copy_password(self):
        acc = self._selected_account()
        if not acc: return
        pwd = acc.get("password","")
        if not pwd:
            messagebox.showinfo("提示","该账号未保存密码"); return
        self.clipboard_clear(); self.clipboard_append(pwd)
        self.status.config(text="✓ 密码已复制（10秒后清除）", fg=ACCENT2)
        def clear():
            import time; time.sleep(10)
            try: self.clipboard_clear()
            except: pass
            self.after(0, lambda: self.status.config(text="", fg=TEXT_DIM))
        threading.Thread(target=clear, daemon=True).start()

    # ── 启动应用 ──────────────────────────────────
    def _launch_app(self):
        acc = self._selected_account()
        if not acc: return
        path = acc.get("app_path","").strip()
        if not path or not os.path.exists(path):
            # 自动搜索
            name = acc.get("platform","")
            found = next((p for n,p in self._installed_apps
                          if name.lower() in n.lower()), None)
            if found: path = found
        if not path or not os.path.exists(path):
            messagebox.showwarning("未找到应用",
                f"未找到「{acc.get('platform','')}」\n请在编辑时手动指定应用路径")
            return
        import datetime
        acc["last_used"] = datetime.datetime.now().strftime("%m-%d %H:%M")
        save_accounts(self.accounts); self._refresh()
        os.startfile(path)
        self.status.config(
            text=f"✓ 已启动「{acc.get('platform','')}」账号：{acc.get('username','')}",
            fg=ACCENT2)


if __name__ == "__main__":
    AccountManager().mainloop()

import os, sys, json, subprocess, base64, threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_USER_DATA  = os.path.join(os.environ.get("APPDATA", SCRIPT_DIR), "KHY小工具")
os.makedirs(_USER_DATA, exist_ok=True)
ACCOUNTS_FILE = os.path.join(_USER_DATA, "accounts.enc")
KEY_FILE      = os.path.join(_USER_DATA, "accounts.key")

BG="#1e1e2e"; BG2="#2a2a3e"; BG3="#313145"
ACCENT="#7c9ef8"; ACCENT2="#a6e3a1"; DANGER="#f38ba8"
TEXT="#cdd6f4"; TEXT_DIM="#6c7086"; BTN="#45475a"

# ══════════════════════════════════════════════════════
# 加密/解密（AES-128，密钥本地存储）
# ══════════════════════════════════════════════════════
def _get_or_create_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()
    key = os.urandom(16)
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return key

def _encrypt(data: str) -> bytes:
    try:
        from cryptography.fernet import Fernet
        key = base64.urlsafe_b64encode(_get_or_create_key() * 2 + b"=" * 4)[:44] + b"="
        return Fernet(key).encrypt(data.encode("utf-8"))
    except ImportError:
        return base64.b64encode(data.encode("utf-8"))

def _decrypt(data: bytes) -> str:
    try:
        from cryptography.fernet import Fernet
        key = base64.urlsafe_b64encode(_get_or_create_key() * 2 + b"=" * 4)[:44] + b"="
        return Fernet(key).decrypt(data).decode("utf-8")
    except ImportError:
        return base64.b64decode(data).decode("utf-8")

def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        return []
    try:
        with open(ACCOUNTS_FILE, "rb") as f:
            raw = _decrypt(f.read())
        return json.loads(raw)
    except Exception:
        return []

def save_accounts(accounts):
    raw = json.dumps(accounts, ensure_ascii=False)
    with open(ACCOUNTS_FILE, "wb") as f:
        f.write(_encrypt(raw))

# ══════════════════════════════════════════════════════
# 预设平台
# ══════════════════════════════════════════════════════
PLATFORMS = {
    "腾讯视频": {"icon": "🎬", "app_names": ["腾讯视频", "QQLive"]},
    "优酷":     {"icon": "🎥", "app_names": ["优酷", "Youku"]},
    "爱奇艺":   {"icon": "🎞", "app_names": ["爱奇艺", "iQIYI"]},
    "芒果TV":   {"icon": "🥭", "app_names": ["芒果TV", "MangoTV"]},
    "哔哩哔哩": {"icon": "📺", "app_names": ["哔哩哔哩", "Bilibili"]},
    "网易云音乐":{"icon":"🎵", "app_names": ["网易云音乐", "CloudMusic"]},
    "QQ音乐":   {"icon": "🎶", "app_names": ["QQ音乐", "QQMusic"]},
    "Steam":    {"icon": "🎮", "app_names": ["Steam"]},
    "其他":     {"icon": "🔑", "app_names": []},
}

# ══════════════════════════════════════════════════════
# 主界面
# ══════════════════════════════════════════════════════
class AccountManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("账号管理工具")
        self.geometry("860x580")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.accounts = load_accounts()
        self._selected = None
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        # 顶部
        top = tk.Frame(self, bg=BG2, pady=10); top.pack(fill="x")
        tk.Label(top, text="🔑  账号管理工具", bg=BG2, fg=ACCENT,
                 font=("微软雅黑",14,"bold")).pack(side="left", padx=20)
        tk.Label(top, text="密码已加密存储，仅保存在本机", bg=BG2, fg=TEXT_DIM,
                 font=("微软雅黑",9)).pack(side="right", padx=20)

        # 搜索 + 分组筛选
        bar = tk.Frame(self, bg=BG, pady=6); bar.pack(fill="x", padx=16)
        tk.Label(bar, text="搜索：", bg=BG, fg=TEXT, font=("微软雅黑",10)).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh())
        tk.Entry(bar, textvariable=self.search_var, bg=BG2, fg=TEXT,
                 insertbackground=TEXT, relief="flat",
                 font=("微软雅黑",10), width=20).pack(side="left", padx=6, ipady=4)
        tk.Label(bar, text="平台：", bg=BG, fg=TEXT, font=("微软雅黑",10)).pack(side="left", padx=(12,0))
        self.filter_var = tk.StringVar(value="全部")
        self._filter_combo = ttk.Combobox(bar, textvariable=self.filter_var,
                                           values=["全部"] + list(PLATFORMS.keys()),
                                           width=10, state="readonly")
        self._filter_combo.pack(side="left", padx=4)
        self._filter_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh())

        # 操作按钮
        for txt, color, cmd in [
            ("＋ 添加账号", ACCENT,  self._add_account),
            ("✎ 编辑",      BTN,     self._edit_account),
            ("✕ 删除",      DANGER,  self._delete_account),
            ("📋 复制密码",  BTN,     self._copy_password),
            ("▶ 启动应用",  ACCENT2, self._launch_app),
        ]:
            tk.Button(bar, text=txt, bg=color, fg=BG if color != BTN else TEXT,
                      relief="flat", font=("微软雅黑",10), padx=10, pady=5,
                      cursor="hand2", command=cmd).pack(side="left", padx=3)

        # 账号列表
        cols = ("平台", "账号/用户名", "备注", "应用路径", "上次使用")
        style = ttk.Style(); style.theme_use("clam")
        style.configure("Acc.Treeview", background=BG2, foreground=TEXT,
                        fieldbackground=BG2, rowheight=34, font=("微软雅黑",10))
        style.configure("Acc.Treeview.Heading", background=BG3, foreground=ACCENT,
                        font=("微软雅黑",10,"bold"))
        style.map("Acc.Treeview", background=[("selected","#3d3d5c")],
                  foreground=[("selected", ACCENT)])

        tree_frame = tk.Frame(self, bg=BG)
        tree_frame.pack(fill="both", expand=True, padx=16, pady=4)
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                  style="Acc.Treeview")
        for col, w in zip(cols, [100, 160, 160, 220, 100]):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, minwidth=60)
        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", lambda e: self._launch_app())

        # 底部状态
        self.status = tk.Label(self, text="", bg=BG, fg=TEXT_DIM,
                                font=("微软雅黑",9), anchor="w")
        self.status.pack(fill="x", padx=16, pady=4)

    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        kw = self.search_var.get().lower()
        plat = self.filter_var.get()
        for i, acc in enumerate(self.accounts):
            if plat != "全部" and acc.get("platform") != plat:
                continue
            if kw and kw not in acc.get("username","").lower() \
                   and kw not in acc.get("note","").lower() \
                   and kw not in acc.get("platform","").lower():
                continue
            icon = PLATFORMS.get(acc.get("platform","其他"), {}).get("icon","🔑")
            self.tree.insert("", "end", iid=str(i), values=(
                f"{icon} {acc.get('platform','')}",
                acc.get("username",""),
                acc.get("note",""),
                acc.get("app_path","") or "未设置",
                acc.get("last_used","从未"),
            ))
        total = len(self.accounts)
        self.status.config(text=f"共 {total} 个账号")

    def _on_select(self, event=None):
        sel = self.tree.selection()
        self._selected = int(sel[0]) if sel else None

    def _selected_account(self):
        if self._selected is None:
            messagebox.showwarning("提示", "请先选择一个账号")
            return None
        return self.accounts[self._selected]

    # ── 添加账号 ──────────────────────────────────
    def _add_account(self):
        self._open_account_dialog()

    def _edit_account(self):
        acc = self._selected_account()
        if acc:
            self._open_account_dialog(acc, self._selected)

    def _open_account_dialog(self, acc=None, idx=None):
        win = tk.Toplevel(self)
        win.title("添加账号" if acc is None else "编辑账号")
        win.geometry("480x400")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.grab_set()

        fields = {}
        defaults = acc or {}

        def row(label, key, show=""):
            r = tk.Frame(win, bg=BG); r.pack(fill="x", padx=24, pady=6)
            tk.Label(r, text=label, bg=BG, fg=TEXT, font=("微软雅黑",10),
                     width=12, anchor="w").pack(side="left")
            v = tk.StringVar(value=defaults.get(key, ""))
            e = tk.Entry(r, textvariable=v, bg=BG2, fg=TEXT, insertbackground=TEXT,
                         relief="flat", font=("微软雅黑",10), show=show, width=28)
            e.pack(side="left", padx=6, ipady=4)
            fields[key] = v
            return v

        tk.Label(win, text="平台：", bg=BG, fg=TEXT,
                 font=("微软雅黑",10)).pack(anchor="w", padx=24, pady=(16,0))
        plat_row = tk.Frame(win, bg=BG); plat_row.pack(fill="x", padx=24, pady=4)
        plat_var = tk.StringVar(value=defaults.get("platform","腾讯视频"))
        ttk.Combobox(plat_row, textvariable=plat_var,
                     values=list(PLATFORMS.keys()), width=16,
                     state="readonly").pack(side="left")
        fields["platform"] = plat_var

        row("账号/用户名", "username")
        row("密码",        "password", show="*")

        # 密码显示切换
        pwd_row = tk.Frame(win, bg=BG); pwd_row.pack(anchor="w", padx=24)
        def toggle_pwd():
            entries = [w for w in win.winfo_children()
                       if isinstance(w, tk.Frame)]
            # 找密码 Entry
            for child in win.winfo_children():
                if isinstance(child, tk.Frame):
                    for w in child.winfo_children():
                        if isinstance(w, tk.Entry) and w.cget("show") in ("*",""):
                            w.config(show="" if w.cget("show")=="*" else "*")
        tk.Button(pwd_row, text="👁 显示/隐藏密码", bg=BG3, fg=TEXT_DIM,
                  relief="flat", font=("微软雅黑",9), cursor="hand2",
                  command=toggle_pwd).pack(side="left")

        row("备注",        "note")

        # 应用路径
        app_row = tk.Frame(win, bg=BG); app_row.pack(fill="x", padx=24, pady=6)
        tk.Label(app_row, text="应用路径：", bg=BG, fg=TEXT,
                 font=("微软雅黑",10), width=12, anchor="w").pack(side="left")
        app_var = tk.StringVar(value=defaults.get("app_path",""))
        fields["app_path"] = app_var
        tk.Entry(app_row, textvariable=app_var, bg=BG2, fg=TEXT,
                 insertbackground=TEXT, relief="flat",
                 font=("微软雅黑",10), width=22).pack(side="left", padx=6, ipady=4)
        tk.Button(app_row, text="📁", bg=BG3, fg=TEXT, relief="flat",
                  cursor="hand2", font=("微软雅黑",10),
                  command=lambda: app_var.set(
                      filedialog.askopenfilename(
                          filetypes=[("应用程序","*.exe *.lnk"),("所有","*.*")]
                      ) or app_var.get()
                  )).pack(side="left")

        def save():
            data = {k: v.get().strip() for k, v in fields.items()}
            if not data.get("username"):
                messagebox.showwarning("提示", "账号不能为空", parent=win)
                return
            data["last_used"] = defaults.get("last_used", "从未")
            if idx is not None:
                self.accounts[idx] = data
            else:
                self.accounts.append(data)
            save_accounts(self.accounts)
            self._refresh()
            win.destroy()

        tk.Button(win, text="💾 保存", bg=ACCENT, fg=BG, relief="flat",
                  font=("微软雅黑",11), padx=24, pady=8, cursor="hand2",
                  command=save).pack(pady=12)

    # ── 删除 ──────────────────────────────────────
    def _delete_account(self):
        acc = self._selected_account()
        if not acc:
            return
        if messagebox.askyesno("确认", f"删除账号「{acc.get('username')}」？"):
            self.accounts.pop(self._selected)
            save_accounts(self.accounts)
            self._selected = None
            self._refresh()

    # ── 复制密码 ──────────────────────────────────
    def _copy_password(self):
        acc = self._selected_account()
        if not acc:
            return
        pwd = acc.get("password","")
        if not pwd:
            messagebox.showinfo("提示", "该账号未保存密码")
            return
        self.clipboard_clear()
        self.clipboard_append(pwd)
        self.status.config(text="✓ 密码已复制到剪贴板（10秒后清除）", fg=ACCENT2)
        # 10秒后清除剪贴板
        def clear_clip():
            import time; time.sleep(10)
            try:
                self.clipboard_clear()
                self.after(0, lambda: self.status.config(
                    text="剪贴板已清除", fg=TEXT_DIM))
            except Exception:
                pass
        threading.Thread(target=clear_clip, daemon=True).start()

    # ── 启动应用 ──────────────────────────────────
    def _launch_app(self):
        acc = self._selected_account()
        if not acc:
            return
        app_path = acc.get("app_path","").strip()

        # 没有配置路径，自动搜索开始菜单
        if not app_path or not os.path.exists(app_path):
            platform = acc.get("platform","")
            app_names = PLATFORMS.get(platform, {}).get("app_names", [platform])
            app_path = self._find_app(app_names)

        if not app_path:
            messagebox.showwarning("未找到应用",
                f"未找到「{acc.get('platform','')}」的应用程序\n"
                f"请在编辑账号时手动指定应用路径")
            return

        # 更新上次使用时间
        import datetime
        acc["last_used"] = datetime.datetime.now().strftime("%m-%d %H:%M")
        save_accounts(self.accounts)
        self._refresh()

        # 启动
        ext = os.path.splitext(app_path)[1].lower()
        if ext == ".lnk":
            os.startfile(app_path)
        elif ext == ".exe":
            subprocess.Popen([app_path], shell=False)
        else:
            os.startfile(app_path)

        self.status.config(
            text=f"✓ 已启动「{acc.get('platform','')}」，账号：{acc.get('username','')}",
            fg=ACCENT2)

    def _find_app(self, names):
        import glob
        for menu_dir in [
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu"),
            os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu"),
            os.path.expandvars(r"%USERPROFILE%\Desktop"),
            r"C:\Users\Public\Desktop",
        ]:
            for fpath in glob.glob(os.path.join(menu_dir, "**", "*.lnk"),
                                   recursive=True):
                fname = os.path.splitext(os.path.basename(fpath))[0].lower()
                for name in names:
                    if name.lower() in fname:
                        return fpath
        return None


if __name__ == "__main__":
    AccountManager().mainloop()
