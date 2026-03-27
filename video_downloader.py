#!/usr/bin/env python3
"""
网页视频下载器
基于 yt-dlp，支持 B站、YouTube、Twitter、抖音等数百个平台
依赖：pip install yt-dlp
"""
import os, sys, threading, subprocess
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SAVE = os.path.join(os.path.expanduser("~"), "Downloads", "视频下载")

BG="#1e1e2e"; BG2="#2a2a3e"; BG3="#313145"
ACCENT="#7c9ef8"; ACCENT2="#a6e3a1"; DANGER="#f38ba8"
TEXT="#cdd6f4"; TEXT_DIM="#6c7086"

def _ensure_ytdlp():
    try:
        import yt_dlp
        return True
    except ImportError:
        return False

class VideoDownloader(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("网页视频下载器")
        self.geometry("700x560")
        self.configure(bg=BG)
        self.resizable(True, True)
        self._downloading = False
        self._build_ui()
        self._check_deps()

    def _build_ui(self):
        # 标题
        top = tk.Frame(self, bg=BG2, pady=10)
        top.pack(fill="x")
        tk.Label(top, text="🎬  网页视频下载器", bg=BG2, fg=ACCENT,
                 font=("微软雅黑",14,"bold")).pack(side="left", padx=20)
        self.status_lbl = tk.Label(top, text="● 就绪", bg=BG2, fg=TEXT_DIM,
                                    font=("微软雅黑",10))
        self.status_lbl.pack(side="right", padx=20)

        # URL 输入
        url_frame = tk.Frame(self, bg=BG, pady=8)
        url_frame.pack(fill="x", padx=16)
        tk.Label(url_frame, text="视频链接：", bg=BG, fg=TEXT,
                 font=("微软雅黑",10)).pack(anchor="w")
        input_row = tk.Frame(url_frame, bg=BG)
        input_row.pack(fill="x", pady=4)
        self.url_var = tk.StringVar()
        self.url_entry = tk.Entry(input_row, textvariable=self.url_var,
                                   bg=BG2, fg=TEXT, insertbackground=TEXT,
                                   relief="flat", font=("微软雅黑",11))
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0,8))
        self.url_entry.bind("<Return>", lambda e: self._start_download())
        tk.Button(input_row, text="粘贴", bg=BG3, fg=TEXT, relief="flat",
                  font=("微软雅黑",10), padx=10, cursor="hand2",
                  command=self._paste_url).pack(side="left", padx=2)
        tk.Button(input_row, text="清空", bg=BG3, fg=TEXT, relief="flat",
                  font=("微软雅黑",10), padx=10, cursor="hand2",
                  command=lambda: self.url_var.set("")).pack(side="left")

        # 选项区
        opt_frame = tk.Frame(self, bg=BG, pady=4)
        opt_frame.pack(fill="x", padx=16)

        # 画质选择
        q_frame = tk.Frame(opt_frame, bg=BG)
        q_frame.pack(side="left")
        tk.Label(q_frame, text="画质：", bg=BG, fg=TEXT,
                 font=("微软雅黑",10)).pack(side="left")
        self.quality_var = tk.StringVar(value="最高画质")
        quality_opts = ["最高画质", "1080p", "720p", "480p", "360p", "仅音频(mp3)"]
        ttk.Combobox(q_frame, textvariable=self.quality_var,
                     values=quality_opts, width=14, state="readonly",
                     font=("微软雅黑",10)).pack(side="left", padx=6)

        # 保存路径
        path_frame = tk.Frame(opt_frame, bg=BG)
        path_frame.pack(side="left", padx=20)
        tk.Label(path_frame, text="保存到：", bg=BG, fg=TEXT,
                 font=("微软雅黑",10)).pack(side="left")
        self.save_var = tk.StringVar(value=DEFAULT_SAVE)
        tk.Entry(path_frame, textvariable=self.save_var, bg=BG2, fg=TEXT,
                 insertbackground=TEXT, relief="flat",
                 font=("微软雅黑",9), width=22).pack(side="left", padx=4)
        tk.Button(path_frame, text="📁", bg=BG3, fg=TEXT, relief="flat",
                  cursor="hand2", font=("微软雅黑",10),
                  command=self._pick_dir).pack(side="left")

        # 下载按钮
        btn_frame = tk.Frame(self, bg=BG, pady=8)
        btn_frame.pack(fill="x", padx=16)
        self.dl_btn = tk.Button(btn_frame, text="⬇ 开始下载", bg=ACCENT, fg=BG,
                                 relief="flat", font=("微软雅黑",11,"bold"),
                                 padx=24, pady=8, cursor="hand2",
                                 command=self._start_download)
        self.dl_btn.pack(side="left", padx=4)
        tk.Button(btn_frame, text="📋 获取视频信息", bg=BG3, fg=TEXT,
                  relief="flat", font=("微软雅黑",10), padx=14, pady=8,
                  cursor="hand2", command=self._get_info).pack(side="left", padx=4)
        tk.Button(btn_frame, text="📂 打开下载目录", bg=BG3, fg=TEXT,
                  relief="flat", font=("微软雅黑",10), padx=14, pady=8,
                  cursor="hand2", command=self._open_dir).pack(side="left", padx=4)
        self.stop_btn = tk.Button(btn_frame, text="⏹ 停止", bg=DANGER, fg=BG,
                                   relief="flat", font=("微软雅黑",10),
                                   padx=14, pady=8, cursor="hand2",
                                   command=self._stop_download, state="disabled")
        self.stop_btn.pack(side="left", padx=4)

        # 进度条
        self.progress = ttk.Progressbar(self, mode="indeterminate", length=400)
        self.progress.pack(fill="x", padx=16, pady=4)

        # 日志
        self.log = scrolledtext.ScrolledText(self, bg=BG2, fg=TEXT,
            font=("Consolas",9), relief="flat", state="disabled", height=14)
        self.log.pack(fill="both", expand=True, padx=16, pady=8)
        self.log.tag_config("ok",  foreground=ACCENT2)
        self.log.tag_config("err", foreground=DANGER)
        self.log.tag_config("info",foreground=ACCENT)

        self._log("支持平台：B站、YouTube、Twitter/X、抖音、微博、TikTok 等数百个网站", "info")
        self._log("粘贴视频链接后点击「开始下载」即可", "info")

    def _log(self, msg, tag=""):
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n", tag)
        self.log.see("end")
        self.log.config(state="disabled")

    def _set_status(self, text, color=TEXT_DIM):
        self.status_lbl.config(text=text, fg=color)

    def _paste_url(self):
        try:
            self.url_var.set(self.clipboard_get())
        except Exception:
            pass

    def _pick_dir(self):
        d = filedialog.askdirectory(title="选择保存目录")
        if d:
            self.save_var.set(d)

    def _open_dir(self):
        d = self.save_var.get()
        os.makedirs(d, exist_ok=True)
        subprocess.Popen(["explorer", d], shell=False)

    def _check_deps(self):
        if not _ensure_ytdlp():
            self._log("⚠ 未安装 yt-dlp，正在自动安装...", "err")
            def install():
                r = subprocess.run([sys.executable, "-m", "pip", "install", "yt-dlp"],
                                   capture_output=True, text=True)
                if r.returncode == 0:
                    self.after(0, lambda: self._log("✓ yt-dlp 安装成功", "ok"))
                else:
                    self.after(0, lambda: self._log(f"✗ 安装失败：{r.stderr[:200]}", "err"))
            threading.Thread(target=install, daemon=True).start()

    def _get_format(self):
        q = self.quality_var.get()
        if q == "最高画质":   return "bestvideo+bestaudio/best"
        if q == "1080p":      return "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
        if q == "720p":       return "bestvideo[height<=720]+bestaudio/best[height<=720]"
        if q == "480p":       return "bestvideo[height<=480]+bestaudio/best[height<=480]"
        if q == "360p":       return "bestvideo[height<=360]+bestaudio/best[height<=360]"
        if "音频" in q:       return "bestaudio/best"
        return "best"

    def _get_info(self):
        url = self.url_var.get().strip()
        if not url:
            self._log("请先输入视频链接", "err"); return
        self._log(f"正在获取视频信息：{url}", "info")
        def do():
            try:
                import yt_dlp
                with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                title    = info.get("title", "未知")
                uploader = info.get("uploader", "未知")
                duration = info.get("duration", 0)
                mins, secs = divmod(int(duration), 60)
                fmts = info.get("formats", [])
                resolutions = sorted(set(
                    f"{f.get('height')}p" for f in fmts
                    if f.get("height") and f.get("vcodec") != "none"
                ), key=lambda x: int(x[:-1]), reverse=True)
                self.after(0, lambda: self._log(
                    f"✓ 标题：{title}\n  UP主：{uploader}\n"
                    f"  时长：{mins}分{secs}秒\n"
                    f"  可用画质：{', '.join(resolutions[:6]) or '未知'}", "ok"))
            except Exception as e:
                self.after(0, lambda: self._log(f"✗ 获取失败：{e}", "err"))
        threading.Thread(target=do, daemon=True).start()

    def _start_download(self):
        if self._downloading:
            return
        url = self.url_var.get().strip()
        if not url:
            self._log("请先输入视频链接", "err"); return
        if not _ensure_ytdlp():
            self._log("yt-dlp 未安装，请稍等自动安装完成", "err"); return

        save_dir = self.save_var.get().strip() or DEFAULT_SAVE
        os.makedirs(save_dir, exist_ok=True)

        self._downloading = True
        self.dl_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.progress.start(10)
        self._set_status("● 下载中...", ACCENT)
        self._log(f"开始下载：{url}", "info")

        def progress_hook(d):
            if d["status"] == "downloading":
                pct = d.get("_percent_str", "").strip()
                speed = d.get("_speed_str", "").strip()
                eta = d.get("_eta_str", "").strip()
                msg = f"  下载中 {pct}  速度：{speed}  剩余：{eta}"
                self.after(0, lambda m=msg: self._log(m))
            elif d["status"] == "finished":
                fname = os.path.basename(d.get("filename",""))
                self.after(0, lambda f=fname: self._log(f"✓ 下载完成：{f}", "ok"))

        def do():
            try:
                import yt_dlp
                fmt = self._get_format()
                is_audio = "音频" in self.quality_var.get()
                opts = {
                    "format": fmt,
                    "outtmpl": os.path.join(save_dir, "%(title)s.%(ext)s"),
                    "progress_hooks": [progress_hook],
                    "quiet": True,
                    "no_warnings": True,
                    "merge_output_format": "mp4",
                }
                if is_audio:
                    opts["postprocessors"] = [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                    }]
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
                self.after(0, lambda: self._on_done(True))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._log(f"✗ 下载失败：{err}", "err"))
                self.after(0, lambda: self._on_done(False))

        self._dl_thread = threading.Thread(target=do, daemon=True)
        self._dl_thread.start()

    def _stop_download(self):
        self._downloading = False
        self._log("已请求停止下载", "err")
        self._on_done(False)

    def _on_done(self, success):
        self._downloading = False
        self.progress.stop()
        self.dl_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self._set_status("● 就绪" if success else "● 已停止",
                         ACCENT2 if success else TEXT_DIM)

if __name__ == "__main__":
    VideoDownloader().mainloop()
