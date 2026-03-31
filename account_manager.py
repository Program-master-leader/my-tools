#!/usr/bin/env python3
"""
账号管理工具（可独立运行，也可嵌入管理中心）
- 任意软件账号存储（本机加密）
- 扫描电脑上的应用快捷方式并一键启动
- 账号支持绑定代理（供爬虫/数据源切换 IP 使用）

依赖（可选）：pip install cryptography
"""

from __future__ import annotations

import base64
import datetime
import glob
import json
import os
import subprocess
import threading
from typing import List, Tuple, Optional, Dict, Any

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import proxy_pool


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_USER_DATA = os.path.join(os.environ.get("APPDATA", SCRIPT_DIR), "KHY小工具")
os.makedirs(_USER_DATA, exist_ok=True)

ACCOUNTS_FILE = os.path.join(_USER_DATA, "accounts.enc")
KEY_FILE = os.path.join(_USER_DATA, "accounts.key")

BG = "#1e1e2e"
BG2 = "#2a2a3e"
BG3 = "#313145"
ACCENT = "#7c9ef8"
ACCENT2 = "#a6e3a1"
DANGER = "#f38ba8"
TEXT = "#cdd6f4"
TEXT_DIM = "#6c7086"
BTN = "#45475a"


def _get_or_create_key() -> bytes:
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()
    key = os.urandom(16)
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return key


def _fernet_key() -> bytes:
    """
    Fernet 需要 32 bytes urlsafe base64 key。
    这里用 16 bytes 本地 key 扩展到 32 bytes（不追求跨机迁移，只追求本机可用）。
    """
    raw = (_get_or_create_key() * 2)[:32]
    return base64.urlsafe_b64encode(raw)


def _encrypt(data: str) -> bytes:
    try:
        from cryptography.fernet import Fernet

        return Fernet(_fernet_key()).encrypt(data.encode("utf-8"))
    except Exception:
        return base64.b64encode(data.encode("utf-8"))


def _decrypt(data: bytes) -> str:
    try:
        from cryptography.fernet import Fernet

        return Fernet(_fernet_key()).decrypt(data).decode("utf-8")
    except Exception:
        return base64.b64decode(data).decode("utf-8")


def load_accounts() -> List[Dict[str, Any]]:
    if not os.path.exists(ACCOUNTS_FILE):
        return []
    try:
        with open(ACCOUNTS_FILE, "rb") as f:
            raw = _decrypt(f.read())
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_accounts(accounts: List[Dict[str, Any]]) -> None:
    raw = json.dumps(accounts, ensure_ascii=False)
    with open(ACCOUNTS_FILE, "wb") as f:
        f.write(_encrypt(raw))


def scan_installed_apps() -> List[Tuple[str, str]]:
    """扫描开始菜单和桌面快捷方式，返回 [(显示名, 路径)]"""
    results: List[Tuple[str, str]] = []
    seen = set()
    search_dirs = [
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu"),
        os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu"),
        os.path.expandvars(r"%USERPROFILE%\Desktop"),
        r"C:\Users\Public\Desktop",
    ]
    for d in search_dirs:
        if not os.path.exists(d):
            continue
        for fpath in glob.glob(os.path.join(d, "**", "*.lnk"), recursive=True):
            name = os.path.splitext(os.path.basename(fpath))[0]
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            results.append((name, fpath))
    results.sort(key=lambda x: x[0].lower())
    return results


class AccountManagerFrame(tk.Frame):
    """
    可嵌入到任意 Tk 容器的账号管理界面。
    如果想独立窗口运行，用 `open_account_manager_window()`。
    """

    def __init__(self, master: tk.Misc, *, title: str = "账号管理工具"):
        super().__init__(master, bg=BG)
        self._title = title
        self.accounts = load_accounts()
        self._selected: Optional[int] = None
        self._installed_apps: List[Tuple[str, str]] = []
        self._active_app: Optional[Tuple[str, str]] = None  # (name, lnk_path)
        self._build_ui()
        self._refresh()
        threading.Thread(target=self._scan_apps_bg, daemon=True).start()

    def _scan_apps_bg(self) -> None:
        self._installed_apps = scan_installed_apps()
        self.after(0, self._refresh_apps)

    def _build_ui(self) -> None:
        top = tk.Frame(self, bg=BG2, pady=10)
        top.pack(fill="x")
        tk.Label(
            top, text="🔑  账号管理", bg=BG2, fg=ACCENT, font=("微软雅黑", 14, "bold")
        ).pack(side="left", padx=20)
        tk.Label(
            top, text="账号/密码仅本机加密保存", bg=BG2, fg=TEXT_DIM, font=("微软雅黑", 9)
        ).pack(side="right", padx=20)

        bar = tk.Frame(self, bg=BG, pady=6)
        bar.pack(fill="x", padx=16)
        tk.Label(bar, text="搜索：", bg=BG, fg=TEXT, font=("微软雅黑", 10)).pack(
            side="left"
        )
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh())
        tk.Entry(
            bar,
            textvariable=self.search_var,
            bg=BG2,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("微软雅黑", 10),
            width=20,
        ).pack(side="left", padx=6, ipady=4)

        for txt, color, cmd in [
            ("＋ 添加账号", ACCENT, self._add_account),
            ("✎ 编辑", BTN, self._edit_account),
            ("✕ 删除", DANGER, self._delete_account),
            ("📋 复制密码", BTN, self._copy_password),
            ("▶ 启动应用", ACCENT2, self._launch_app),
            ("🌐 代理池", BG3, self._open_proxy_pool_dialog),
        ]:
            tk.Button(
                bar,
                text=txt,
                bg=color,
                fg=BG if color not in (BTN,) else TEXT,
                relief="flat",
                font=("微软雅黑", 10),
                padx=10,
                pady=5,
                cursor="hand2",
                command=cmd,
            ).pack(side="left", padx=3)

        # 主区：左应用列表，右账号列表
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=16, pady=4)

        left = tk.Frame(main, bg=BG2, width=260)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        tk.Label(left, text="应用清单（点击进入账号）", bg=BG2, fg=ACCENT, font=("微软雅黑", 10, "bold")).pack(
            anchor="w", padx=12, pady=(10, 6)
        )
        self.app_search_var = tk.StringVar()
        self.app_search_var.trace_add("write", lambda *_: self._refresh_apps())
        tk.Entry(
            left,
            textvariable=self.app_search_var,
            bg=BG3,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("微软雅黑", 10),
        ).pack(fill="x", padx=12, ipady=4)

        self.apps_lb = tk.Listbox(
            left,
            bg=BG3,
            fg=TEXT,
            font=("微软雅黑", 10),
            selectbackground="#3d3d5c",
            relief="flat",
            activestyle="none",
        )
        self.apps_lb.pack(fill="both", expand=True, padx=12, pady=10)
        self.apps_lb.bind("<<ListboxSelect>>", lambda e: self._on_app_select())
        self.apps_lb.bind("<Double-1>", lambda e: self._launch_selected_app())

        # 右侧账号表
        right = tk.Frame(main, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))

        self.active_app_label = tk.Label(
            right, text="当前应用：全部账号", bg=BG, fg=TEXT_DIM, font=("微软雅黑", 10), anchor="w"
        )
        self.active_app_label.pack(fill="x", pady=(0, 6))

        cols = ("软件/平台", "账号", "备注", "代理/IP", "应用", "上次使用")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Acc.Treeview",
            background=BG2,
            foreground=TEXT,
            fieldbackground=BG2,
            rowheight=34,
            font=("微软雅黑", 10),
        )
        style.configure(
            "Acc.Treeview.Heading",
            background=BG3,
            foreground=ACCENT,
            font=("微软雅黑", 10, "bold"),
        )
        style.map(
            "Acc.Treeview",
            background=[("selected", "#3d3d5c")],
            foreground=[("selected", ACCENT)],
        )

        tf = tk.Frame(right, bg=BG)
        tf.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tf, columns=cols, show="headings", style="Acc.Treeview")
        for col, w in zip(cols, [120, 150, 140, 120, 140, 90]):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, minwidth=60)
        sb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", lambda e: self._launch_app())

        self.status = tk.Label(self, text="", bg=BG, fg=TEXT_DIM, font=("微软雅黑", 9), anchor="w")
        self.status.pack(fill="x", padx=16, pady=4)
        self._refresh_apps()

    def _refresh(self) -> None:
        self.tree.delete(*self.tree.get_children())
        kw = (self.search_var.get() or "").lower().strip()
        shown = 0
        for i, acc in enumerate(self.accounts):
            if self._active_app and acc.get("platform", "") != self._active_app[0]:
                continue
            if kw and not any(
                kw in str(acc.get(k, "")).lower() for k in ("platform", "username", "note", "proxy")
            ):
                continue
            app_name = os.path.splitext(os.path.basename(acc.get("app_path", "")))[0] or "未设置"
            proxy_raw = str(acc.get("proxy", "") or "")
            proxy_norm = proxy_pool.normalize_proxy_value(proxy_raw)
            proxy = "代理池" if (not proxy_norm or proxy_norm == "POOL") else proxy_norm
            self.tree.insert(
                "",
                "end",
                iid=str(i),
                values=(
                    acc.get("platform", ""),
                    acc.get("username", ""),
                    acc.get("note", ""),
                    proxy,
                    app_name,
                    acc.get("last_used", "从未"),
                ),
            )
            shown += 1
        scope = f"「{self._active_app[0]}」" if self._active_app else "全部"
        self.status.config(text=f"{scope}：显示 {shown} / 共 {len(self.accounts)} 个账号")

    def _refresh_apps(self) -> None:
        kw = (getattr(self, "app_search_var", tk.StringVar()).get() or "").lower().strip()
        apps = self._installed_apps or []
        # 列表第一项：全部
        display = ["全部账号"]
        for name, _path in apps:
            if kw and kw not in name.lower():
                continue
            display.append(name)
        cur = self.apps_lb.curselection()
        cur_name = self.apps_lb.get(cur[0]) if cur else None
        self.apps_lb.delete(0, "end")
        for item in display:
            self.apps_lb.insert("end", item)
        # 尽量保持选中
        if cur_name and cur_name in display:
            self.apps_lb.selection_set(display.index(cur_name))
        elif self._active_app:
            if self._active_app[0] in display:
                self.apps_lb.selection_set(display.index(self._active_app[0]))

    def _on_app_select(self) -> None:
        sel = self.apps_lb.curselection()
        if not sel:
            return
        name = self.apps_lb.get(sel[0])
        if name == "全部账号":
            self._active_app = None
            self.active_app_label.config(text="当前应用：全部账号", fg=TEXT_DIM)
            self._refresh()
            return
        path = next((p for n, p in self._installed_apps if n == name), "")
        self._active_app = (name, path)
        self.active_app_label.config(text=f"当前应用：{name}", fg=ACCENT)
        self._refresh()

    def _launch_selected_app(self) -> None:
        if not self._active_app:
            return
        try:
            os.startfile(self._active_app[1])
        except Exception:
            pass

    def _on_select(self, _e=None) -> None:
        sel = self.tree.selection()
        self._selected = int(sel[0]) if sel else None

    def _selected_account(self) -> Optional[Dict[str, Any]]:
        if self._selected is None:
            messagebox.showwarning("提示", "请先选择一个账号")
            return None
        if self._selected < 0 or self._selected >= len(self.accounts):
            return None
        return self.accounts[self._selected]

    def _add_account(self) -> None:
        # 若已选中应用，则预填 platform / app_path
        if self._active_app:
            self._open_dialog({"platform": self._active_app[0], "app_path": self._active_app[1], "proxy": "POOL"})
        else:
            self._open_dialog()

    def _edit_account(self) -> None:
        acc = self._selected_account()
        if acc:
            self._open_dialog(acc, self._selected)

    def _open_dialog(self, acc: Optional[Dict[str, Any]] = None, idx: Optional[int] = None) -> None:
        win = tk.Toplevel(self)
        win.title("添加账号" if acc is None else "编辑账号")
        win.geometry("520x500")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.grab_set()

        d = acc or {}
        fields: Dict[str, tk.StringVar] = {}

        def row(label: str, key: str, *, show: str = "", hint: str = "", width: int = 30) -> tk.StringVar:
            r = tk.Frame(win, bg=BG)
            r.pack(fill="x", padx=24, pady=5)
            tk.Label(r, text=label, bg=BG, fg=TEXT, font=("微软雅黑", 10), width=10, anchor="w").pack(
                side="left"
            )
            v = tk.StringVar(value=str(d.get(key, "") or ""))
            e = tk.Entry(
                r,
                textvariable=v,
                bg=BG2,
                fg=TEXT,
                insertbackground=TEXT,
                relief="flat",
                font=("微软雅黑", 10),
                show=show,
                width=width,
            )
            e.pack(side="left", padx=6, ipady=5)
            if hint:
                tk.Label(r, text=hint, bg=BG, fg=TEXT_DIM, font=("微软雅黑", 8)).pack(side="left")
            fields[key] = v
            return v

        tk.Label(win, text="软件/平台名称：", bg=BG, fg=TEXT, font=("微软雅黑", 10)).pack(
            anchor="w", padx=24, pady=(16, 0)
        )

        plat_row = tk.Frame(win, bg=BG)
        plat_row.pack(fill="x", padx=24, pady=5)
        tk.Label(plat_row, text="软件名：", bg=BG, fg=TEXT, font=("微软雅黑", 10), width=10, anchor="w").pack(
            side="left"
        )
        plat_var = tk.StringVar(value=str(d.get("platform", "") or ""))
        tk.Entry(
            plat_row,
            textvariable=plat_var,
            bg=BG2,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("微软雅黑", 10),
            width=20,
        ).pack(side="left", padx=6, ipady=5)
        fields["platform"] = plat_var

        app_path_var = tk.StringVar(value=str(d.get("app_path", "") or ""))

        def pick_from_installed() -> None:
            apps = self._installed_apps or scan_installed_apps()
            self._installed_apps = apps
            if not apps:
                messagebox.showinfo("提示", "未找到已安装应用", parent=win)
                return
            sel_win = tk.Toplevel(win)
            sel_win.title("选择应用")
            sel_win.geometry("420x520")
            sel_win.configure(bg=BG)
            sel_win.grab_set()
            tk.Label(sel_win, text="搜索：", bg=BG, fg=TEXT, font=("微软雅黑", 10)).pack(
                anchor="w", padx=12, pady=(8, 0)
            )
            sv = tk.StringVar()
            tk.Entry(
                sel_win,
                textvariable=sv,
                bg=BG2,
                fg=TEXT,
                insertbackground=TEXT,
                relief="flat",
                font=("微软雅黑", 10),
            ).pack(fill="x", padx=12, ipady=4)
            lb = tk.Listbox(sel_win, bg=BG2, fg=TEXT, font=("微软雅黑", 10), selectbackground="#3d3d5c", relief="flat")
            lb.pack(fill="both", expand=True, padx=12, pady=6)

            def _fill(kw: str = "") -> None:
                lb.delete(0, "end")
                for name, _path in apps:
                    if kw.lower() in name.lower():
                        lb.insert("end", name)

            _fill()
            sv.trace_add("write", lambda *_: _fill(sv.get()))

            def confirm() -> None:
                sel = lb.curselection()
                if not sel:
                    return
                name = lb.get(sel[0])
                path = next(p for n, p in apps if n == name)
                plat_var.set(name)
                app_path_var.set(path)
                sel_win.destroy()

            tk.Button(
                sel_win,
                text="✓ 选择",
                bg=ACCENT,
                fg=BG,
                relief="flat",
                font=("微软雅黑", 10),
                padx=16,
                pady=6,
                cursor="hand2",
                command=confirm,
            ).pack(pady=6)
            lb.bind("<Double-1>", lambda e: confirm())

        tk.Button(
            plat_row,
            text="📱 从已安装应用选择",
            bg=BG3,
            fg=TEXT,
            relief="flat",
            font=("微软雅黑", 9),
            padx=8,
            cursor="hand2",
            command=pick_from_installed,
        ).pack(side="left", padx=4)

        row("账号", "username")
        pwd_var = row("密码", "password", show="*")

        def toggle_pwd() -> None:
            # 找到密码 entry 并切换
            for child in win.winfo_children():
                if isinstance(child, tk.Frame):
                    for w in child.winfo_children():
                        if isinstance(w, tk.Entry) and w.get() == pwd_var.get():
                            w.config(show="" if w.cget("show") == "*" else "*")
                            return

        tk.Button(
            win,
            text="👁 显示/隐藏密码",
            bg=BG3,
            fg=TEXT_DIM,
            relief="flat",
            font=("微软雅黑", 9),
            cursor="hand2",
            command=toggle_pwd,
        ).pack(anchor="w", padx=80, pady=0)

        row("备注", "note", hint="（可选）")

        # 代理选择：支持 “代理池/固定代理”
        proxy_row = tk.Frame(win, bg=BG)
        proxy_row.pack(fill="x", padx=24, pady=5)
        tk.Label(
            proxy_row, text="代理/IP", bg=BG, fg=TEXT, font=("微软雅黑", 10), width=10, anchor="w"
        ).pack(side="left")

        proxy_var = tk.StringVar(value=str(d.get("proxy", "") or "POOL"))
        proxy_var.set(proxy_pool.normalize_proxy_value(proxy_var.get()) or "POOL")
        fields["proxy"] = proxy_var

        ttk.Combobox(
            proxy_row,
            textvariable=proxy_var,
            values=["POOL", ""],
            width=8,
            state="readonly",
        ).pack(side="left", padx=(6, 4))

        proxy_entry = tk.Entry(
            proxy_row,
            bg=BG2,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("微软雅黑", 10),
            width=22,
        )
        proxy_entry.pack(side="left", padx=(0, 6), ipady=5)

        def _sync_proxy_entry(*_):
            v = proxy_var.get()
            if v == "POOL":
                proxy_entry.delete(0, "end")
                proxy_entry.insert(0, "（使用代理池自动轮换）")
                proxy_entry.config(state="disabled", fg=TEXT_DIM)
            elif v == "":
                proxy_entry.config(state="normal", fg=TEXT)
                proxy_entry.delete(0, "end")
                proxy_entry.insert(0, "")
                proxy_entry.focus_set()

        def _use_fixed_proxy():
            proxy_var.set("")
            _sync_proxy_entry()

        tk.Button(
            proxy_row,
            text="固定",
            bg=BG3,
            fg=TEXT_DIM,
            relief="flat",
            font=("微软雅黑", 9),
            cursor="hand2",
            command=_use_fixed_proxy,
        ).pack(side="left")

        # 初始化固定代理值
        fixed_val = proxy_pool.normalize_proxy_value(str(d.get("proxy", "") or ""))
        if fixed_val and fixed_val != "POOL":
            proxy_var.set("")
            proxy_entry.delete(0, "end")
            proxy_entry.insert(0, fixed_val)
        _sync_proxy_entry()
        proxy_var.trace_add("write", _sync_proxy_entry)

        ar = tk.Frame(win, bg=BG)
        ar.pack(fill="x", padx=24, pady=5)
        tk.Label(ar, text="应用路径：", bg=BG, fg=TEXT, font=("微软雅黑", 10), width=10, anchor="w").pack(
            side="left"
        )
        tk.Entry(
            ar,
            textvariable=app_path_var,
            bg=BG2,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("微软雅黑", 9),
            width=28,
        ).pack(side="left", padx=6, ipady=4)
        tk.Button(
            ar,
            text="📁",
            bg=BG3,
            fg=TEXT,
            relief="flat",
            cursor="hand2",
            command=lambda: app_path_var.set(
                filedialog.askopenfilename(filetypes=[("应用", "*.exe *.lnk"), ("所有", "*.*")]) or app_path_var.get()
            ),
        ).pack(side="left")

        def save() -> None:
            data = {k: v.get().strip() for k, v in fields.items()}
            data["app_path"] = app_path_var.get().strip()
            if not data.get("username"):
                messagebox.showwarning("提示", "账号不能为空", parent=win)
                return
            # 如果选择固定代理（proxy_var == ""），从 entry 取值
            if data.get("proxy", "").strip() == "":
                data["proxy"] = proxy_entry.get().strip()
            data["proxy"] = proxy_pool.normalize_proxy_value(str(data.get("proxy", "") or "")) or "POOL"
            data["last_used"] = d.get("last_used", "从未")
            if idx is not None:
                self.accounts[idx] = data
            else:
                self.accounts.append(data)
            save_accounts(self.accounts)
            self._refresh()
            win.destroy()

        tk.Button(
            win,
            text="💾 保存",
            bg=ACCENT,
            fg=BG,
            relief="flat",
            font=("微软雅黑", 11),
            padx=24,
            pady=8,
            cursor="hand2",
            command=save,
        ).pack(pady=10)

    def _delete_account(self) -> None:
        acc = self._selected_account()
        if not acc:
            return
        if messagebox.askyesno("确认", f"删除「{acc.get('username', '')}」？"):
            self.accounts.pop(self._selected or 0)
            save_accounts(self.accounts)
            self._selected = None
            self._refresh()

    def _copy_password(self) -> None:
        acc = self._selected_account()
        if not acc:
            return
        pwd = acc.get("password", "")
        if not pwd:
            messagebox.showinfo("提示", "该账号未保存密码")
            return
        top = self.winfo_toplevel()
        try:
            top.clipboard_clear()
            top.clipboard_append(pwd)
        except Exception:
            return
        self.status.config(text="✓ 密码已复制（10秒后清除）", fg=ACCENT2)

        def clear() -> None:
            import time

            time.sleep(10)
            try:
                top.clipboard_clear()
            except Exception:
                pass
            self.after(0, lambda: self.status.config(text="", fg=TEXT_DIM))

        threading.Thread(target=clear, daemon=True).start()

    def _launch_app(self) -> None:
        acc = self._selected_account()
        if not acc:
            return
        path = (acc.get("app_path", "") or "").strip()
        if not path or not os.path.exists(path):
            name = (acc.get("platform", "") or "").strip()
            found = next((p for n, p in self._installed_apps if name and name.lower() in n.lower()), None)
            if found:
                path = found

        if not path or not os.path.exists(path):
            messagebox.showwarning("未找到应用", f"未找到「{acc.get('platform','')}」\n请在编辑时指定应用路径")
            return

        acc["last_used"] = datetime.datetime.now().strftime("%m-%d %H:%M")
        save_accounts(self.accounts)
        self._refresh()

        try:
            os.startfile(path)
        except Exception as e:
            messagebox.showerror("启动失败", str(e))
            return

        self.status.config(
            text=f"✓ 已启动「{acc.get('platform','')}」账号：{acc.get('username','')}",
            fg=ACCENT2,
        )

    def _open_proxy_pool_dialog(self) -> None:
        """
        代理池配置：维护 proxies.json
        """
        win = tk.Toplevel(self)
        win.title("代理池管理")
        win.geometry("620x460")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.grab_set()

        cfg = proxy_pool.load_config()

        # 顶部设置
        top = tk.Frame(win, bg=BG)
        top.pack(fill="x", padx=16, pady=(16, 8))
        tk.Label(top, text="轮换模式：", bg=BG, fg=TEXT, font=("微软雅黑", 10)).pack(side="left")
        mode_var = tk.StringVar(value=str(cfg.get("mode", "round_robin")))
        ttk.Combobox(
            top,
            textvariable=mode_var,
            values=["round_robin", "random"],
            width=14,
            state="readonly",
        ).pack(side="left", padx=6)
        tk.Label(top, text="失败冷却(秒)：", bg=BG, fg=TEXT, font=("微软雅黑", 10)).pack(side="left", padx=(16, 0))
        cooldown_var = tk.StringVar(value=str(cfg.get("cooldown_sec", 120)))
        tk.Entry(top, textvariable=cooldown_var, bg=BG2, fg=TEXT, insertbackground=TEXT, relief="flat", width=8).pack(
            side="left", padx=6, ipady=3
        )

        # 列表
        mid = tk.Frame(win, bg=BG)
        mid.pack(fill="both", expand=True, padx=16, pady=6)

        cols = ("名称", "代理", "启用")
        tree = ttk.Treeview(mid, columns=cols, show="headings", height=12)
        for c, w in zip(cols, [160, 340, 60]):
            tree.heading(c, text=c)
            tree.column(c, width=w, anchor="w")
        tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(mid, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

        def refresh():
            tree.delete(*tree.get_children())
            items = cfg.get("items", []) if isinstance(cfg.get("items", []), list) else []
            for i, it in enumerate(items):
                if not isinstance(it, dict):
                    continue
                tree.insert(
                    "",
                    "end",
                    iid=str(i),
                    values=(it.get("name", ""), it.get("proxy", ""), "✓" if it.get("enabled", True) else ""),
                )

        refresh()

        def selected_index() -> Optional[int]:
            sel = tree.selection()
            if not sel:
                return None
            try:
                return int(sel[0])
            except Exception:
                return None

        def edit_item(idx: Optional[int] = None):
            d = {}
            if idx is not None:
                try:
                    d = cfg.get("items", [])[idx]
                except Exception:
                    d = {}

            ew = tk.Toplevel(win)
            ew.title("添加代理" if idx is None else "编辑代理")
            ew.geometry("520x220")
            ew.configure(bg=BG)
            ew.resizable(False, False)
            ew.grab_set()

            name_var = tk.StringVar(value=str(d.get("name", "") or ""))
            proxy_var2 = tk.StringVar(value=str(d.get("proxy", "") or ""))
            enabled_var = tk.BooleanVar(value=bool(d.get("enabled", True)))

            def r(label, var, width=40):
                row = tk.Frame(ew, bg=BG)
                row.pack(fill="x", padx=20, pady=8)
                tk.Label(row, text=label, bg=BG, fg=TEXT, font=("微软雅黑", 10), width=8, anchor="w").pack(side="left")
                tk.Entry(row, textvariable=var, bg=BG2, fg=TEXT, insertbackground=TEXT, relief="flat", width=width).pack(
                    side="left", padx=6, ipady=4
                )

            r("名称", name_var)
            r("代理", proxy_var2)

            cb_row = tk.Frame(ew, bg=BG)
            cb_row.pack(fill="x", padx=20, pady=4)
            tk.Checkbutton(cb_row, text="启用", variable=enabled_var, bg=BG, fg=TEXT, selectcolor=BG3, activebackground=BG).pack(
                side="left"
            )

            def save():
                name = name_var.get().strip() or proxy_var2.get().strip()
                proxy = proxy_var2.get().strip()
                if not proxy:
                    messagebox.showwarning("提示", "代理不能为空", parent=ew)
                    return
                it = {"name": name, "proxy": proxy, "enabled": bool(enabled_var.get())}
                if idx is None:
                    cfg.setdefault("items", []).append(it)
                else:
                    cfg.setdefault("items", [])[idx] = it
                refresh()
                ew.destroy()

            tk.Button(ew, text="保存", bg=ACCENT, fg=BG, relief="flat", font=("微软雅黑", 10), padx=18, pady=6, command=save).pack(
                pady=10
            )

        def add():
            edit_item(None)

        def edit():
            idx = selected_index()
            if idx is None:
                return
            edit_item(idx)

        def delete():
            idx = selected_index()
            if idx is None:
                return
            items = cfg.get("items", [])
            if not isinstance(items, list) or idx >= len(items):
                return
            if messagebox.askyesno("确认", "删除该代理？", parent=win):
                items.pop(idx)
                cfg["items"] = items
                refresh()

        def toggle_enabled():
            idx = selected_index()
            if idx is None:
                return
            items = cfg.get("items", [])
            if not isinstance(items, list) or idx >= len(items):
                return
            items[idx]["enabled"] = not bool(items[idx].get("enabled", True))
            refresh()

        # 底部按钮
        bottom = tk.Frame(win, bg=BG)
        bottom.pack(fill="x", padx=16, pady=(6, 12))
        tk.Button(bottom, text="＋ 添加", bg=ACCENT, fg=BG, relief="flat", font=("微软雅黑", 10), padx=12, pady=6, command=add).pack(
            side="left", padx=4
        )
        tk.Button(bottom, text="✎ 编辑", bg=BTN, fg=TEXT, relief="flat", font=("微软雅黑", 10), padx=12, pady=6, command=edit).pack(
            side="left", padx=4
        )
        tk.Button(bottom, text="✓ 启用/禁用", bg=BG3, fg=TEXT, relief="flat", font=("微软雅黑", 10), padx=12, pady=6, command=toggle_enabled).pack(
            side="left", padx=4
        )
        tk.Button(bottom, text="✕ 删除", bg=DANGER, fg=BG, relief="flat", font=("微软雅黑", 10), padx=12, pady=6, command=delete).pack(
            side="left", padx=4
        )

        def save_all():
            cfg["mode"] = (mode_var.get() or "round_robin").strip()
            try:
                cfg["cooldown_sec"] = int(float(cooldown_var.get().strip() or "120"))
            except Exception:
                cfg["cooldown_sec"] = 120
            proxy_pool.save_config(cfg)
            messagebox.showinfo("完成", "代理池已保存", parent=win)
            win.destroy()

        tk.Button(bottom, text="💾 保存", bg=ACCENT2, fg=BG, relief="flat", font=("微软雅黑", 10), padx=18, pady=6, command=save_all).pack(
            side="right", padx=4
        )


def open_account_manager_window() -> None:
    root = tk.Tk()
    root.title("账号管理工具")
    root.geometry("980x620")
    root.configure(bg=BG)
    root.resizable(True, True)
    frame = AccountManagerFrame(root)
    frame.pack(fill="both", expand=True)
    root.mainloop()


if __name__ == "__main__":
    open_account_manager_window()
