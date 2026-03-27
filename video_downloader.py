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
        self.geometry("780x620")
        self.configure(bg=BG)
        self.resizable(True, True)
        self._downloading = False
        self._playlist_items = []  # [(checked_var, title, url, duration)]
        self._build_ui()
        self._check_deps()

    def _build_ui(self):
        # 标题栏
        top = tk.Frame(self, bg=BG2, pady=10)
        top.pack(fill="x")
        tk.Label(top, text="🎬  网页视频下载器", bg=BG2, fg=ACCENT,
                 font=("微软雅黑",14,"bold")).pack(side="left", padx=20)
        self.status_lbl = tk.Label(top, text="● 就绪", bg=BG2, fg=TEXT_DIM,
                                    font=("微软雅黑",10))
        self.status_lbl.pack(side="right", padx=20)

        # Notebook 标签页
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG3, foreground=TEXT,
                        font=("微软雅黑",10), padding=[12,6])
        style.map("TNotebook.Tab", background=[("selected", BG2)],
                  foreground=[("selected", ACCENT)])

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=4)

        self._tab_single = tk.Frame(nb, bg=BG)
        self._tab_batch  = tk.Frame(nb, bg=BG)
        nb.add(self._tab_single, text="  单视频下载  ")
        nb.add(self._tab_batch,  text="  批量/播放列表  ")

        self._build_single_tab()
        self._build_batch_tab()

    # ══════════════════════════════════════════════
    # 单视频标签页
    # ══════════════════════════════════════════════
    def _build_single_tab(self):
        f = self._tab_single

    # ══════════════════════════════════════════════
    # 单视频标签页
    # ══════════════════════════════════════════════
    def _build_single_tab(self):
        f = self._tab_single

        # URL 输入
        url_frame = tk.Frame(f, bg=BG, pady=8)
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

        # ── 高级设置（折叠面板）──────────────────────
        adv_toggle = tk.Frame(self, bg=BG)
        adv_toggle.pack(fill="x", padx=16, pady=(2,0))
        self._adv_open = tk.BooleanVar(value=False)
        self._adv_btn = tk.Button(adv_toggle, text="▶ 高级设置",
                                   bg=BG, fg=TEXT_DIM, relief="flat",
                                   font=("微软雅黑",9), cursor="hand2",
                                   command=self._toggle_adv)
        self._adv_btn.pack(side="left")

        self._adv_frame = tk.Frame(self, bg=BG2, padx=12, pady=8)
        # 不 pack，折叠时隐藏

        # 第一行：UA + 限速
        r1 = tk.Frame(self._adv_frame, bg=BG2); r1.pack(fill="x", pady=2)
        tk.Label(r1, text="User-Agent：", bg=BG2, fg=TEXT,
                 font=("微软雅黑",9), width=12, anchor="w").pack(side="left")
        self.ua_var = tk.StringVar(value="random")
        ua_opts = ["random", "Chrome/Windows", "Firefox/Windows",
                   "Safari/Mac", "Chrome/Android", "自定义"]
        self._ua_combo = ttk.Combobox(r1, textvariable=self.ua_var,
                                       values=ua_opts, width=18, state="readonly")
        self._ua_combo.pack(side="left", padx=4)
        self._ua_combo.bind("<<ComboboxSelected>>", self._on_ua_change)

        tk.Label(r1, text="限速：", bg=BG2, fg=TEXT,
                 font=("微软雅黑",9)).pack(side="left", padx=(16,4))
        self.speed_var = tk.StringVar(value="不限速")
        ttk.Combobox(r1, textvariable=self.speed_var,
                     values=["不限速","500K","1M","2M","5M"],
                     width=8, state="readonly").pack(side="left")

        tk.Label(r1, text="重试次数：", bg=BG2, fg=TEXT,
                 font=("微软雅黑",9)).pack(side="left", padx=(16,4))
        self.retry_var = tk.StringVar(value="3")
        ttk.Combobox(r1, textvariable=self.retry_var,
                     values=["1","3","5","10"],
                     width=4, state="readonly").pack(side="left")

        # 自定义UA输入框（默认隐藏）
        self._custom_ua_frame = tk.Frame(self._adv_frame, bg=BG2)
        tk.Label(self._custom_ua_frame, text="自定义UA：", bg=BG2, fg=TEXT,
                 font=("微软雅黑",9), width=12, anchor="w").pack(side="left")
        self.custom_ua_var = tk.StringVar()
        tk.Entry(self._custom_ua_frame, textvariable=self.custom_ua_var,
                 bg=BG3, fg=TEXT, insertbackground=TEXT, relief="flat",
                 font=("微软雅黑",9), width=60).pack(side="left", fill="x", expand=True)

        # 第二行：代理
        r2 = tk.Frame(self._adv_frame, bg=BG2); r2.pack(fill="x", pady=2)
        tk.Label(r2, text="代理地址：", bg=BG2, fg=TEXT,
                 font=("微软雅黑",9), width=12, anchor="w").pack(side="left")
        self.proxy_var = tk.StringVar(placeholder="留空不使用代理，如：http://127.0.0.1:7890")
        self.proxy_var = tk.StringVar()
        tk.Entry(r2, textvariable=self.proxy_var, bg=BG3, fg=TEXT,
                 insertbackground=TEXT, relief="flat", font=("微软雅黑",9), width=36
                 ).pack(side="left", padx=4)
        tk.Label(r2, text="（如：http://127.0.0.1:7890）", bg=BG2, fg=TEXT_DIM,
                 font=("微软雅黑",8)).pack(side="left")

        # 第三行：Cookie
        r3 = tk.Frame(self._adv_frame, bg=BG2); r3.pack(fill="x", pady=2)
        tk.Label(r3, text="Cookie文件：", bg=BG2, fg=TEXT,
                 font=("微软雅黑",9), width=12, anchor="w").pack(side="left")
        self.cookie_var = tk.StringVar()
        tk.Entry(r3, textvariable=self.cookie_var, bg=BG3, fg=TEXT,
                 insertbackground=TEXT, relief="flat", font=("微软雅黑",9), width=30
                 ).pack(side="left", padx=4)
        tk.Button(r3, text="📁 选择文件", bg=BG3, fg=TEXT, relief="flat",
                  font=("微软雅黑",9), cursor="hand2",
                  command=self._pick_cookie).pack(side="left", padx=2)

        # 从浏览器自动提取 Cookie
        r4 = tk.Frame(self._adv_frame, bg=BG2); r4.pack(fill="x", pady=4)
        tk.Label(r4, text="从浏览器提取：", bg=BG2, fg=TEXT,
                 font=("微软雅黑",9), width=12, anchor="w").pack(side="left")
        self.browser_var = tk.StringVar(value="chrome")
        browsers = ["chrome", "edge", "firefox", "brave", "opera", "vivaldi"]
        ttk.Combobox(r4, textvariable=self.browser_var,
                     values=browsers, width=10, state="readonly").pack(side="left", padx=4)
        tk.Button(r4, text="🍪 提取Cookie", bg=ACCENT, fg=BG,
                  relief="flat", font=("微软雅黑",9), padx=10, cursor="hand2",
                  command=self._extract_browser_cookie).pack(side="left", padx=4)
        self.cookie_status = tk.Label(r4, text="", bg=BG2, fg=ACCENT2,
                                       font=("微软雅黑",9))
        self.cookie_status.pack(side="left", padx=4)
        tk.Label(r4, text="（需先在浏览器登录B站/YouTube等）",
                 bg=BG2, fg=TEXT_DIM, font=("微软雅黑",8)).pack(side="left")

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

    def _pick_cookie(self):
        f = filedialog.askopenfilename(
            title="选择Cookie文件",
            filetypes=[("Cookie文件","*.txt *.json"),("所有文件","*.*")])
        if f:
            self.cookie_var.set(f)

    def _extract_browser_cookie(self):
        """用 yt-dlp 直接从浏览器提取 Cookie，保存到本地文件"""
        if not _ensure_ytdlp():
            self._log("请先等待 yt-dlp 安装完成", "err"); return
        browser = self.browser_var.get()
        save_path = os.path.join(os.path.expanduser("~"), f".khy_{browser}_cookies.txt")
        self.cookie_status.config(text="⏳ 提取中...", fg=ACCENT)
        def do():
            try:
                import yt_dlp
                # yt-dlp 支持直接从浏览器读取 cookie
                opts = {
                    "cookiesfrombrowser": (browser,),
                    "cookiefile": save_path,
                    "quiet": True,
                    "skip_download": True,
                }
                # 用一个简单的公开视频测试并顺便保存 cookie
                test_urls = {
                    "bilibili": "https://www.bilibili.com",
                    "youtube":  "https://www.youtube.com",
                }
                # 直接导出 cookie 不需要 URL
                with yt_dlp.YoutubeDL(opts) as ydl:
                    # 触发 cookie 读取和保存
                    try:
                        ydl.extract_info("https://www.bilibili.com/video/BV1xx411c7mD",
                                         download=False)
                    except Exception:
                        pass  # 不在乎视频信息，只要 cookie 被保存了
                if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                    self.after(0, lambda: [
                        self.cookie_var.set(save_path),
                        self.cookie_status.config(
                            text=f"✓ 已提取 {browser} Cookie", fg=ACCENT2),
                        self._log(f"✓ Cookie 已从 {browser} 提取并保存", "ok")
                    ])
                else:
                    self.after(0, lambda: [
                        self.cookie_status.config(text="✗ 提取失败", fg=DANGER),
                        self._log(f"✗ 未能从 {browser} 提取 Cookie，请确认浏览器已登录且已关闭", "err")
                    ])
            except Exception as e:
                err = str(e)
                self.after(0, lambda: [
                    self.cookie_status.config(text="✗ 提取失败", fg=DANGER),
                    self._log(f"✗ Cookie 提取失败：{err[:150]}", "err")
                ])
        threading.Thread(target=do, daemon=True).start()

    def _toggle_adv(self):
        if self._adv_open.get():
            self._adv_frame.pack_forget()
            self._adv_open.set(False)
            self._adv_btn.config(text="▶ 高级设置")
        else:
            self._adv_frame.pack(fill="x", padx=16, pady=2, before=self.progress)
            self._adv_open.set(True)
            self._adv_btn.config(text="▼ 高级设置")

    def _on_ua_change(self, event=None):
        if self.ua_var.get() == "自定义":
            self._custom_ua_frame.pack(fill="x", pady=2)
        else:
            self._custom_ua_frame.pack_forget()

    def _get_ua(self):
        import random
        ua_map = {
            "Chrome/Windows": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Firefox/Windows": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
            "Safari/Mac": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Chrome/Android": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
        }
        sel = self.ua_var.get()
        if sel == "random":
            return random.choice(list(ua_map.values()))
        if sel == "自定义":
            return self.custom_ua_var.get().strip() or ua_map["Chrome/Windows"]
        return ua_map.get(sel, ua_map["Chrome/Windows"])

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
                with yt_dlp.YoutubeDL({
                    "quiet": True,
                    "http_headers": {"User-Agent": self._get_ua()},
                }) as ydl:
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
                    # 防封IP优化
                    "http_headers": {"User-Agent": self._get_ua()},
                    "retries": int(self.retry_var.get()),
                    "fragment_retries": int(self.retry_var.get()),
                    "sleep_interval": 1,        # 请求间隔1秒
                    "max_sleep_interval": 3,    # 最多随机等3秒
                    "sleep_interval_requests": 1,
                }
                # 限速
                speed = self.speed_var.get()
                if speed != "不限速":
                    opts["ratelimit"] = speed
                # 代理
                proxy = self.proxy_var.get().strip()
                if proxy:
                    opts["proxy"] = proxy
                # Cookie：优先文件，其次直接读浏览器
                cookie = self.cookie_var.get().strip()
                if cookie and os.path.exists(cookie):
                    opts["cookiefile"] = cookie
                elif not cookie:
                    # 没有指定文件时，尝试直接从选定浏览器读取
                    browser = self.browser_var.get()
                    opts["cookiesfrombrowser"] = (browser,)
                    self._log(f"  使用 {browser} 浏览器 Cookie（需已登录）")
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

    # ══════════════════════════════════════════════
    # 批量/播放列表标签页
    # ══════════════════════════════════════════════
    def _build_batch_tab(self):
        f = self._tab_batch

        # URL 输入
        top = tk.Frame(f, bg=BG, pady=8); top.pack(fill="x", padx=16)
        tk.Label(top, text="播放列表 / UP主主页 / 搜索结果页链接：",
                 bg=BG, fg=TEXT, font=("微软雅黑",10)).pack(anchor="w")
        row = tk.Frame(top, bg=BG); row.pack(fill="x", pady=4)
        self.batch_url_var = tk.StringVar()
        tk.Entry(row, textvariable=self.batch_url_var, bg=BG2, fg=TEXT,
                 insertbackground=TEXT, relief="flat",
                 font=("微软雅黑",11)).pack(side="left", fill="x", expand=True,
                                           ipady=8, padx=(0,8))
        tk.Button(row, text="粘贴", bg=BG3, fg=TEXT, relief="flat",
                  font=("微软雅黑",10), padx=10, cursor="hand2",
                  command=lambda: self.batch_url_var.set(
                      self.clipboard_get())).pack(side="left", padx=2)

        # 扫描选项
        opt = tk.Frame(f, bg=BG); opt.pack(fill="x", padx=16, pady=4)
        tk.Label(opt, text="最多扫描：", bg=BG, fg=TEXT,
                 font=("微软雅黑",10)).pack(side="left")
        self.batch_limit_var = tk.StringVar(value="50")
        ttk.Combobox(opt, textvariable=self.batch_limit_var,
                     values=["10","20","50","100","全部"],
                     width=6, state="readonly").pack(side="left", padx=4)
        tk.Label(opt, text="个视频", bg=BG, fg=TEXT,
                 font=("微软雅黑",10)).pack(side="left")

        # 扫描按钮
        btn_row = tk.Frame(f, bg=BG); btn_row.pack(fill="x", padx=16, pady=4)
        self.scan_btn = tk.Button(btn_row, text="🔍 开始扫描", bg="#89b4fa", fg=BG,
                                   relief="flat", font=("微软雅黑",11,"bold"),
                                   padx=20, pady=8, cursor="hand2",
                                   command=self._scan_playlist)
        self.scan_btn.pack(side="left", padx=4)
        tk.Button(btn_row, text="✓ 全选", bg=BG3, fg=TEXT, relief="flat",
                  font=("微软雅黑",10), padx=12, pady=8, cursor="hand2",
                  command=self._select_all).pack(side="left", padx=2)
        tk.Button(btn_row, text="✗ 全不选", bg=BG3, fg=TEXT, relief="flat",
                  font=("微软雅黑",10), padx=12, pady=8, cursor="hand2",
                  command=self._deselect_all).pack(side="left", padx=2)
        self.batch_dl_btn = tk.Button(btn_row, text="⬇ 下载选中", bg=ACCENT2, fg=BG,
                                       relief="flat", font=("微软雅黑",11,"bold"),
                                       padx=20, pady=8, cursor="hand2",
                                       command=self._batch_download, state="disabled")
        self.batch_dl_btn.pack(side="left", padx=4)
        self.batch_count_lbl = tk.Label(btn_row, text="", bg=BG, fg=TEXT_DIM,
                                         font=("微软雅黑",9))
        self.batch_count_lbl.pack(side="left", padx=8)

        # 视频列表（带复选框）
        list_frame = tk.Frame(f, bg=BG); list_frame.pack(fill="both", expand=True,
                                                           padx=16, pady=4)
        # 列头
        hdr = tk.Frame(list_frame, bg=BG3); hdr.pack(fill="x")
        tk.Label(hdr, text="  ✓", bg=BG3, fg=ACCENT, font=("微软雅黑",9,"bold"),
                 width=3).pack(side="left")
        tk.Label(hdr, text="标题", bg=BG3, fg=ACCENT, font=("微软雅黑",9,"bold"),
                 width=40, anchor="w").pack(side="left")
        tk.Label(hdr, text="时长", bg=BG3, fg=ACCENT, font=("微软雅黑",9,"bold"),
                 width=8).pack(side="left")
        tk.Label(hdr, text="状态", bg=BG3, fg=ACCENT, font=("微软雅黑",9,"bold"),
                 width=8).pack(side="left")

        # 滚动列表
        canvas = tk.Canvas(list_frame, bg=BG2, highlightthickness=0)
        sb = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self._batch_list_frame = tk.Frame(canvas, bg=BG2)
        self._batch_canvas_win = canvas.create_window(
            (0,0), window=self._batch_list_frame, anchor="nw")
        self._batch_list_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(self._batch_canvas_win, width=e.width))
        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))

        # 扫描进度条
        self.batch_progress = ttk.Progressbar(f, mode="indeterminate")
        self.batch_progress.pack(fill="x", padx=16, pady=2)

    def _scan_playlist(self):
        url = self.batch_url_var.get().strip()
        if not url:
            return
        if not _ensure_ytdlp():
            return
        # 清空列表
        for w in self._batch_list_frame.winfo_children():
            w.destroy()
        self._playlist_items.clear()
        self.batch_dl_btn.config(state="disabled")
        self.batch_count_lbl.config(text="扫描中...")
        self.scan_btn.config(state="disabled")
        self.batch_progress.start(10)

        limit_str = self.batch_limit_var.get()
        limit = None if limit_str == "全部" else int(limit_str)

        def do():
            try:
                import yt_dlp
                opts = {
                    "quiet": True,
                    "extract_flat": True,   # 只获取列表，不下载
                    "http_headers": {"User-Agent": self._get_ua()},
                }
                if limit:
                    opts["playlistend"] = limit

                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)

                entries = []
                if info.get("_type") == "playlist" or info.get("entries"):
                    entries = list(info.get("entries") or [])
                else:
                    # 单个视频
                    entries = [info]

                self.after(0, lambda: self._render_playlist(entries))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: [
                    self.batch_count_lbl.config(text=f"扫描失败：{err[:60]}"),
                    self.scan_btn.config(state="normal"),
                    self.batch_progress.stop()
                ])

        threading.Thread(target=do, daemon=True).start()

    def _render_playlist(self, entries):
        self.batch_progress.stop()
        self.scan_btn.config(state="normal")
        self._playlist_items.clear()

        for w in self._batch_list_frame.winfo_children():
            w.destroy()

        for i, entry in enumerate(entries):
            if not entry:
                continue
            title    = (entry.get("title") or entry.get("id") or f"视频{i+1}")[:50]
            duration = entry.get("duration") or 0
            video_url = entry.get("url") or entry.get("webpage_url") or ""
            mins, secs = divmod(int(duration), 60)
            dur_str = f"{mins}:{secs:02d}" if duration else "--:--"

            checked = tk.BooleanVar(value=True)
            status_var = tk.StringVar(value="待下载")
            self._playlist_items.append((checked, title, video_url, status_var))

            row_bg = BG2 if i % 2 == 0 else BG3
            row = tk.Frame(self._batch_list_frame, bg=row_bg)
            row.pack(fill="x", pady=1)

            tk.Checkbutton(row, variable=checked, bg=row_bg,
                           activebackground=row_bg,
                           command=self._update_count).pack(side="left", padx=4)
            tk.Label(row, text=title, bg=row_bg, fg=TEXT,
                     font=("微软雅黑",9), width=42, anchor="w").pack(side="left")
            tk.Label(row, text=dur_str, bg=row_bg, fg=TEXT_DIM,
                     font=("微软雅黑",9), width=8).pack(side="left")
            tk.Label(row, textvariable=status_var, bg=row_bg, fg=ACCENT2,
                     font=("微软雅黑",9), width=8).pack(side="left")

        total = len(self._playlist_items)
        self.batch_count_lbl.config(text=f"共 {total} 个视频，已全选")
        if total > 0:
            self.batch_dl_btn.config(state="normal")

    def _update_count(self):
        selected = sum(1 for v, *_ in self._playlist_items if v.get())
        total = len(self._playlist_items)
        self.batch_count_lbl.config(text=f"已选 {selected}/{total} 个")

    def _select_all(self):
        for v, *_ in self._playlist_items: v.set(True)
        self._update_count()

    def _deselect_all(self):
        for v, *_ in self._playlist_items: v.set(False)
        self._update_count()

    def _batch_download(self):
        selected = [(t, u, sv) for v, t, u, sv in self._playlist_items if v.get()]
        if not selected:
            return
        save_dir = self.save_var.get().strip() or DEFAULT_SAVE
        os.makedirs(save_dir, exist_ok=True)
        self.batch_dl_btn.config(state="disabled")
        self.batch_progress.start(10)
        self._set_status(f"● 批量下载 0/{len(selected)}", ACCENT)

        def do():
            import yt_dlp
            done = 0
            for title, url, status_var in selected:
                if not url:
                    self.after(0, lambda sv=status_var: sv.set("无链接"))
                    continue
                self.after(0, lambda sv=status_var: sv.set("下载中"))
                try:
                    opts = {
                        "format": self._get_format(),
                        "outtmpl": os.path.join(save_dir, "%(title)s.%(ext)s"),
                        "quiet": True,
                        "no_warnings": True,
                        "merge_output_format": "mp4",
                        "http_headers": {"User-Agent": self._get_ua()},
                        "retries": int(self.retry_var.get()),
                    }
                    cookie = self.cookie_var.get().strip()
                    if cookie and os.path.exists(cookie):
                        opts["cookiefile"] = cookie
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        ydl.download([url])
                    done += 1
                    self.after(0, lambda sv=status_var: sv.set("✓ 完成"))
                    self.after(0, lambda d=done, t=len(selected):
                               self._set_status(f"● 批量下载 {d}/{t}", ACCENT))
                except Exception as e:
                    self.after(0, lambda sv=status_var: sv.set("✗ 失败"))
            self.after(0, lambda: [
                self.batch_progress.stop(),
                self.batch_dl_btn.config(state="normal"),
                self._set_status(f"● 完成 {done}/{len(selected)}", ACCENT2)
            ])

        threading.Thread(target=do, daemon=True).start()


if __name__ == "__main__":
    VideoDownloader().mainloop()
