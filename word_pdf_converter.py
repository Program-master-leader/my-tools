#!/usr/bin/env python3
"""Word ↔ PDF 转换工具"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

BG      = "#1e1e2e"
BG2     = "#2a2a3e"
BG3     = "#313145"
ACCENT  = "#7c9ef8"
ACCENT2 = "#a6e3a1"
DANGER  = "#f38ba8"
TEXT    = "#cdd6f4"
TEXT_DIM= "#6c7086"
BTN_BG  = "#45475a"
BTN_HOV = "#585b70"


def check_deps():
    missing = []
    try:
        import docx2pdf
    except ImportError:
        missing.append("docx2pdf")
    try:
        import pdf2docx
    except ImportError:
        missing.append("pdf2docx")
    return missing


def install_deps(log_fn):
    import subprocess
    for dep in ["docx2pdf", "pdf2docx"]:
        log_fn(f"安装 {dep}...")
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", dep, "-q",
             "--disable-pip-version-check"],
            capture_output=True)
        log_fn(f"  {'✓' if r.returncode == 0 else '✗'} {dep}")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Word ↔ PDF 转换工具")
        self.geometry("680x520")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.files = []  # [(原路径, 转换方向)]
        self._build_ui()
        self._check_deps_async()

    def _build_ui(self):
        # 标题
        top = tk.Frame(self, bg=BG2, pady=10)
        top.pack(fill="x")
        tk.Label(top, text="📄  Word ↔ PDF 转换工具",
                 bg=BG2, fg=ACCENT, font=("微软雅黑", 14, "bold")).pack(side="left", padx=20)

        # 模式选择
        mode_frame = tk.Frame(self, bg=BG, pady=8)
        mode_frame.pack(fill="x", padx=20)
        tk.Label(mode_frame, text="转换方向：", bg=BG, fg=TEXT,
                 font=("微软雅黑", 10)).pack(side="left")
        self.mode = tk.StringVar(value="word2pdf")
        tk.Radiobutton(mode_frame, text="Word → PDF", variable=self.mode,
                       value="word2pdf", bg=BG, fg=TEXT, selectcolor=BG3,
                       activebackground=BG, activeforeground=ACCENT,
                       font=("微软雅黑", 10),
                       command=self._on_mode_change).pack(side="left", padx=12)
        tk.Radiobutton(mode_frame, text="PDF → Word", variable=self.mode,
                       value="pdf2word", bg=BG, fg=TEXT, selectcolor=BG3,
                       activebackground=BG, activeforeground=ACCENT,
                       font=("微软雅黑", 10),
                       command=self._on_mode_change).pack(side="left", padx=4)

        # 拖拽/添加区域
        drop_frame = tk.Frame(self, bg=BG3, pady=14, padx=10)
        drop_frame.pack(fill="x", padx=20, pady=4)
        self.drop_label = tk.Label(
            drop_frame,
            text="📂  将 Word 文件拖拽到此处，或点击「添加文件」",
            bg=BG3, fg=TEXT_DIM, font=("微软雅黑", 9))
        self.drop_label.pack(side="left")
        tk.Button(drop_frame, text="＋ 添加文件", bg=ACCENT, fg=BG,
                  relief="flat", font=("微软雅黑", 9), padx=10, pady=4,
                  cursor="hand2", command=self._add_files).pack(side="right")

        # 尝试启用拖拽
        try:
            from tkinterdnd2 import TkinterDnD, DND_FILES
            drop_frame.drop_target_register(DND_FILES)
            drop_frame.dnd_bind("<<Drop>>", self._on_drop)
        except Exception:
            pass

        # 文件列表
        list_frame = tk.Frame(self, bg=BG)
        list_frame.pack(fill="both", expand=True, padx=20, pady=4)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Conv.Treeview", background=BG2, foreground=TEXT,
                        fieldbackground=BG2, rowheight=28, font=("微软雅黑", 9))
        style.configure("Conv.Treeview.Heading", background=BG3, foreground=ACCENT,
                        font=("微软雅黑", 9, "bold"))
        style.map("Conv.Treeview", background=[("selected", BG3)],
                  foreground=[("selected", ACCENT)])

        cols = ("文件名", "大小", "状态")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings",
                                  style="Conv.Treeview", height=8)
        self.tree.heading("文件名", text="文件名")
        self.tree.heading("大小", text="大小")
        self.tree.heading("状态", text="状态")
        self.tree.column("文件名", width=380)
        self.tree.column("大小", width=80)
        self.tree.column("状态", width=100)
        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # 输出目录
        out_frame = tk.Frame(self, bg=BG, pady=4)
        out_frame.pack(fill="x", padx=20)
        tk.Label(out_frame, text="输出目录：", bg=BG, fg=TEXT,
                 font=("微软雅黑", 9)).pack(side="left")
        self.out_var = tk.StringVar(value="与原文件相同目录")
        tk.Entry(out_frame, textvariable=self.out_var, bg=BG2, fg=TEXT,
                 insertbackground=TEXT, relief="flat",
                 font=("微软雅黑", 9), width=38).pack(side="left", padx=6)
        tk.Button(out_frame, text="浏览", bg=BTN_BG, fg=TEXT, relief="flat",
                  font=("微软雅黑", 9), padx=8, cursor="hand2",
                  command=self._pick_outdir).pack(side="left")

        # 操作按钮
        btn_frame = tk.Frame(self, bg=BG, pady=8)
        btn_frame.pack(fill="x", padx=20)
        tk.Button(btn_frame, text="▶  开始转换", bg=ACCENT, fg=BG,
                  relief="flat", font=("微软雅黑", 11, "bold"),
                  padx=20, pady=8, cursor="hand2",
                  command=self._start_convert).pack(side="left")
        tk.Button(btn_frame, text="清空列表", bg=BTN_BG, fg=TEXT,
                  relief="flat", font=("微软雅黑", 9),
                  padx=12, pady=8, cursor="hand2",
                  command=self._clear).pack(side="left", padx=10)

        # 日志
        self.log_box = tk.Text(self, bg=BG2, fg=TEXT, font=("Consolas", 9),
                                relief="flat", height=5, state="disabled")
        self.log_box.pack(fill="x", padx=20, pady=(0, 12))

    def _log(self, msg):
        self.log_box.config(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def _check_deps_async(self):
        def check():
            missing = check_deps()
            if missing:
                self.after(0, lambda: self._log(
                    f"缺少依赖：{', '.join(missing)}，正在自动安装..."))
                install_deps(lambda m: self.after(0, lambda msg=m: self._log(msg)))
                self.after(0, lambda: self._log("依赖安装完成 ✓"))
        threading.Thread(target=check, daemon=True).start()

    def _on_mode_change(self):
        mode = self.mode.get()
        if mode == "word2pdf":
            self.drop_label.config(text="📂  将 Word 文件拖拽到此处，或点击「添加文件」")
        else:
            self.drop_label.config(text="📂  将 PDF 文件拖拽到此处，或点击「添加文件」")
        self._clear()

    def _on_drop(self, event):
        import re
        raw = event.data.strip()
        paths = re.findall(r'\{([^}]+)\}|(\S+)', raw)
        paths = [a or b for a, b in paths]
        for p in paths:
            self._add_path(p.strip().strip('"'))

    def _add_files(self):
        mode = self.mode.get()
        if mode == "word2pdf":
            ftypes = [("Word文档", "*.docx *.doc"), ("所有文件", "*.*")]
        else:
            ftypes = [("PDF文件", "*.pdf"), ("所有文件", "*.*")]
        paths = filedialog.askopenfilenames(title="选择文件", filetypes=ftypes)
        for p in paths:
            self._add_path(p)

    def _add_path(self, path):
        if not os.path.isfile(path):
            return
        ext = os.path.splitext(path)[1].lower()
        mode = self.mode.get()
        if mode == "word2pdf" and ext not in (".docx", ".doc"):
            self._log(f"跳过（非Word文件）：{os.path.basename(path)}")
            return
        if mode == "pdf2word" and ext != ".pdf":
            self._log(f"跳过（非PDF文件）：{os.path.basename(path)}")
            return
        # 去重
        if path in [f[0] for f in self.files]:
            return
        self.files.append((path, mode))
        size = os.path.getsize(path)
        size_str = f"{size/1024:.0f} KB" if size < 1024*1024 else f"{size/1024/1024:.1f} MB"
        self.tree.insert("", "end", values=(os.path.basename(path), size_str, "等待中"),
                         iid=path)

    def _pick_outdir(self):
        d = filedialog.askdirectory(title="选择输出目录")
        if d:
            self.out_var.set(d)

    def _clear(self):
        self.files.clear()
        self.tree.delete(*self.tree.get_children())

    def _get_outdir(self, src_path):
        val = self.out_var.get().strip()
        if val and val != "与原文件相同目录" and os.path.isdir(val):
            return val
        return os.path.dirname(src_path)

    def _start_convert(self):
        if not self.files:
            messagebox.showwarning("提示", "请先添加文件")
            return
        threading.Thread(target=self._do_convert, daemon=True).start()

    def _do_convert(self):
        total = len(self.files)
        ok_count = 0
        for i, (path, mode) in enumerate(self.files):
            self.after(0, lambda p=path: self.tree.set(p, "状态", "转换中..."))
            try:
                outdir = self._get_outdir(path)
                if mode == "word2pdf":
                    out = self._word_to_pdf(path, outdir)
                else:
                    out = self._pdf_to_word(path, outdir)
                self.after(0, lambda p=path: self.tree.set(p, "状态", "✓ 完成"))
                self.after(0, lambda o=out: self._log(f"✓ {os.path.basename(o)}"))
                ok_count += 1
            except Exception as e:
                self.after(0, lambda p=path: self.tree.set(p, "状态", "✗ 失败"))
                self.after(0, lambda err=str(e), p=path:
                           self._log(f"✗ {os.path.basename(p)}: {err}"))

        self.after(0, lambda: self._log(
            f"\n完成：{ok_count}/{total} 个文件转换成功"))
        if ok_count > 0:
            outdir = self._get_outdir(self.files[0][0])
            self.after(0, lambda d=outdir: messagebox.showinfo(
                "转换完成", f"成功转换 {ok_count} 个文件\n输出目录：{d}"))

    def _word_to_pdf(self, src, outdir):
        from docx2pdf import convert
        name = os.path.splitext(os.path.basename(src))[0] + ".pdf"
        out  = os.path.join(outdir, name)
        convert(src, out)
        return out

    def _pdf_to_word(self, src, outdir):
        from pdf2docx import Converter
        name = os.path.splitext(os.path.basename(src))[0] + ".docx"
        out  = os.path.join(outdir, name)
        cv = Converter(src)
        cv.convert(out, start=0, end=None)
        cv.close()
        return out


if __name__ == "__main__":
    app = App()
    app.mainloop()
