#!/usr/bin/env python3
"""
小K语音助手
唤醒词：小K / 小k / xiaoK
支持：写文章、关机、重启、打开程序、查时间等
"""

import os
import sys
import threading
import queue
import datetime
import subprocess
import tkinter as tk
from tkinter import scrolledtext
import json
import re

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SAVE = "D:\\"
WAKE_WORDS   = ["小k", "小K", "xiaok", "xiaoK", "小可", "小客"]

# ── 颜色 ──────────────────────────────────────────────
BG      = "#1e1e2e"
BG2     = "#2a2a3e"
BG3     = "#313145"
ACCENT  = "#7c9ef8"
ACCENT2 = "#a6e3a1"
DANGER  = "#f38ba8"
TEXT    = "#cdd6f4"
TEXT_DIM= "#6c7086"


# ══════════════════════════════════════════════════════
# 语音识别（用 sounddevice 替代 PyAudio）
# ══════════════════════════════════════════════════════
def record_audio(duration=6, samplerate=16000):
    """用 sounddevice 录音，返回 AudioData 对象供 SpeechRecognition 使用"""
    import sounddevice as sd
    import numpy as np
    import speech_recognition as sr

    audio_np = sd.rec(int(duration * samplerate), samplerate=samplerate,
                      channels=1, dtype="int16")
    sd.wait()
    audio_bytes = audio_np.tobytes()
    audio_data = sr.AudioData(audio_bytes, samplerate, 2)
    return audio_data


def record_and_recognize(timeout=5, phrase_limit=10):
    """录音并识别，返回文字（中文）"""
    import speech_recognition as sr
    r = sr.Recognizer()
    audio = record_audio(duration=phrase_limit)
    try:
        text = r.recognize_google(audio, language="zh-CN")
        return text
    except sr.UnknownValueError:
        return ""
    except Exception as e:
        raise e


# ══════════════════════════════════════════════════════
# AI 生成（Ollama qwen2.5:7b）
# ══════════════════════════════════════════════════════
def ask_ollama(prompt, stream_callback=None):
    """调用本地 Ollama，支持流式输出，自动启动服务"""
    import time
    # 确保 Ollama 服务在运行
    for ollama_path in [r"D:\Ollama\ollama.exe", r"C:\Users\Public\ollama\ollama.exe"]:
        if os.path.exists(ollama_path):
            subprocess.Popen([ollama_path, "serve"],
                             creationflags=0x08000000,  # 不弹窗
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1)
            break
    try:
        import ollama
        result = ""
        stream = ollama.chat(
            model="qwen2.5:7b",
            messages=[{"role": "user", "content": prompt}],
            stream=True)
        for chunk in stream:
            piece = chunk["message"]["content"]
            result += piece
            if stream_callback:
                stream_callback(piece)
        return result
    except Exception as e:
        return f"[AI错误: {e}]"


# ══════════════════════════════════════════════════════
# 指令解析 & 执行
# ══════════════════════════════════════════════════════
def parse_save_path(text):
    """从指令中提取保存路径，默认 D:\\"""
    patterns = [
        r"保存到([A-Za-z]:[^\s，。,\.]+)",
        r"存到([A-Za-z]:[^\s，。,\.]+)",
        r"放到([A-Za-z]:[^\s，。,\.]+)",
        r"保存在([A-Za-z]:[^\s，。,\.]+)",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1).strip()
    return DEFAULT_SAVE


def parse_filename(text):
    """从指令中提取文件名"""
    patterns = [
        r'命名为["\u300c\u300e]?([^\u300d\u300f"\uff0c\u3002\s]+)["\u300d\u300f]?',
        r'文件名[为是]["\u300c\u300e]?([^\u300d\u300f"\uff0c\u3002\s]+)["\u300d\u300f]?',
        r'叫做?["\u300c\u300e]?([^\u300d\u300f"\uff0c\u3002\s]+)["\u300d\u300f]?',
        r'取名[为叫]["\u300c\u300e]?([^\u300d\u300f"\uff0c\u3002\s]+)["\u300d\u300f]?',
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1).strip()
    return None


def parse_format(text):
    """从指令中提取文件格式"""
    if "word" in text.lower() or "docx" in text.lower() or "文档" in text:
        return "docx"
    if "pdf" in text.lower():
        return "pdf"
    if "txt" in text.lower() or "文本" in text:
        return "txt"
    return "txt"  # 默认


def save_as_txt(content, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def save_as_docx(content, path):
    from docx import Document
    doc = Document()
    for line in content.split("\n"):
        doc.add_paragraph(line)
    doc.save(path)


def save_as_pdf(content, path):
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    # 尝试加载中文字体
    font_paths = [
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simsun.ttc",
    ]
    font_loaded = False
    for fp in font_paths:
        if os.path.exists(fp):
            pdf.add_font("CJK", "", fp, uni=True)
            pdf.set_font("CJK", size=12)
            font_loaded = True
            break
    if not font_loaded:
        pdf.set_font("Arial", size=12)
    for line in content.split("\n"):
        pdf.multi_cell(0, 8, line)
    pdf.output(path)


def execute_command(text, log_fn, stream_fn):
    """解析并执行指令，返回结果描述"""
    text_lower = text.lower().strip()

    # ── 系统指令 ──
    if any(w in text for w in ["关机", "关闭电脑", "shutdown"]):
        log_fn("收到关机指令，5秒后关机...")
        subprocess.Popen("shutdown /s /t 5", shell=True)
        return "好的，电脑将在5秒后关机。"

    if any(w in text for w in ["取消关机", "撤销关机"]):
        subprocess.Popen("shutdown /a", shell=True)
        return "已取消关机。"

    if any(w in text for w in ["重启", "重新启动"]):
        log_fn("收到重启指令，5秒后重启...")
        subprocess.Popen("shutdown /r /t 5", shell=True)
        return "好的，电脑将在5秒后重启。"

    if any(w in text for w in ["几点", "时间", "现在多少点"]):
        now = datetime.datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
        return f"现在是 {now}"

    if any(w in text for w in ["打开计算器", "启动计算器"]):
        subprocess.Popen("calc", shell=True)
        return "已打开计算器。"

    if any(w in text for w in ["打开记事本", "启动记事本"]):
        subprocess.Popen("notepad", shell=True)
        return "已打开记事本。"

    if any(w in text for w in ["打开浏览器", "启动浏览器"]):
        subprocess.Popen("start https://www.baidu.com", shell=True)
        return "已打开浏览器。"

    # ── 写文章/内容生成 ──
    write_triggers = ["写", "生成", "帮我写", "写一篇", "写一个", "创作", "起草"]
    is_write = any(w in text for w in write_triggers)

    if is_write:
        fmt      = parse_format(text)
        save_dir = parse_save_path(text)
        fname    = parse_filename(text)

        # 构建 AI 提示词
        # 去掉路径、格式、文件名等元信息，只保留内容需求
        clean = re.sub(r"保存(到|在|为)[^\s，。]+", "", text)
        clean = re.sub(r"(命名为|文件名|叫做?|取名)[^\s，。]+", "", clean)
        clean = re.sub(r"(word|docx|pdf|txt|文档|文本)格式?", "", clean, flags=re.I)
        clean = clean.strip("，。, .")

        log_fn(f"正在生成内容：{clean[:30]}...")
        stream_fn("", clear=True)
        content = ask_ollama(clean, stream_callback=lambda p: stream_fn(p))

        if not content or content.startswith("[AI错误"):
            return f"内容生成失败：{content}"

        # 确定文件名
        if not fname:
            # 从指令里提取主题作为文件名
            fname = re.sub(r"[写帮我生成创作起草一篇个]", "", clean)[:20].strip()
            fname = re.sub(r'[\\/:*?"<>|]', "", fname) or "小K生成"

        os.makedirs(save_dir, exist_ok=True)
        ext_map = {"docx": ".docx", "pdf": ".pdf", "txt": ".txt"}
        full_path = os.path.join(save_dir, fname + ext_map.get(fmt, ".txt"))

        try:
            if fmt == "docx":
                save_as_docx(content, full_path)
            elif fmt == "pdf":
                save_as_pdf(content, full_path)
            else:
                save_as_txt(content, full_path)
            return f"✓ 已保存到：{full_path}"
        except Exception as e:
            return f"保存失败：{e}"

    # ── 兜底：直接问 AI ──
    log_fn("正在思考...")
    stream_fn("", clear=True)
    answer = ask_ollama(text, stream_callback=lambda p: stream_fn(p))
    return answer


# ══════════════════════════════════════════════════════
# GUI
# ══════════════════════════════════════════════════════
class VoiceAssistant(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("小K 语音助手")
        self.geometry("700x560")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.listening = False
        self.wake_mode = False   # 是否处于唤醒监听状态
        self._build_ui()
        self._check_deps()

    def _build_ui(self):
        # 标题栏
        top = tk.Frame(self, bg=BG2, pady=10)
        top.pack(fill="x")
        tk.Label(top, text="🎙  小K 语音助手",
                 bg=BG2, fg=ACCENT, font=("微软雅黑", 14, "bold")).pack(side="left", padx=20)
        self.status_label = tk.Label(top, text="● 待机", bg=BG2, fg=TEXT_DIM,
                                      font=("微软雅黑", 10))
        self.status_label.pack(side="right", padx=20)

        # 对话记录
        self.chat = scrolledtext.ScrolledText(
            self, bg=BG2, fg=TEXT, font=("微软雅黑", 10),
            relief="flat", state="disabled", wrap="word", height=18)
        self.chat.pack(fill="both", expand=True, padx=16, pady=8)
        self.chat.tag_config("user",   foreground=ACCENT)
        self.chat.tag_config("ai",     foreground=ACCENT2)
        self.chat.tag_config("system", foreground=TEXT_DIM)
        self.chat.tag_config("error",  foreground=DANGER)

        # 输入区
        input_frame = tk.Frame(self, bg=BG, pady=6)
        input_frame.pack(fill="x", padx=16)
        self.input_var = tk.StringVar()
        entry = tk.Entry(input_frame, textvariable=self.input_var,
                         bg=BG2, fg=TEXT, insertbackground=TEXT,
                         relief="flat", font=("微软雅黑", 11))
        entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
        entry.bind("<Return>", lambda e: self._send_text())

        tk.Button(input_frame, text="发送", bg=ACCENT, fg=BG,
                  relief="flat", font=("微软雅黑", 10), padx=14, pady=6,
                  cursor="hand2", command=self._send_text).pack(side="left")

        # 按钮区
        btn_frame = tk.Frame(self, bg=BG, pady=6)
        btn_frame.pack(fill="x", padx=16)

        self.mic_btn = tk.Button(
            btn_frame, text="🎙 按住说话", bg="#45475a", fg=TEXT,
            relief="flat", font=("微软雅黑", 10), padx=16, pady=8,
            cursor="hand2")
        self.mic_btn.pack(side="left", padx=4)
        self.mic_btn.bind("<ButtonPress-1>",   self._mic_press)
        self.mic_btn.bind("<ButtonRelease-1>", self._mic_release)

        self.wake_btn = tk.Button(
            btn_frame, text="👂 开启唤醒监听", bg="#45475a", fg=TEXT,
            relief="flat", font=("微软雅黑", 10), padx=16, pady=8,
            cursor="hand2", command=self._toggle_wake)
        self.wake_btn.pack(side="left", padx=4)

        tk.Button(btn_frame, text="清空", bg="#45475a", fg=TEXT,
                  relief="flat", font=("微软雅黑", 10), padx=12, pady=8,
                  cursor="hand2", command=self._clear_chat).pack(side="right", padx=4)

        self._append("system", "小K已就绪。说「小K」唤醒，或直接输入指令。\n"
                                "支持：写文章、关机、重启、查时间、打开程序等。\n")

    def _append(self, tag, text):
        self.chat.config(state="normal")
        prefix = {"user": "👤 你：", "ai": "🤖 小K：",
                  "system": "", "error": "⚠ "}.get(tag, "")
        self.chat.insert("end", prefix + text + "\n", tag)
        self.chat.see("end")
        self.chat.config(state="disabled")

    def _stream_append(self, piece, clear=False):
        """流式追加 AI 输出"""
        self.chat.config(state="normal")
        if clear:
            # 找到最后一行"🤖 小K："并清空其后内容
            idx = self.chat.search("🤖 小K：", "1.0", backwards=True, stopindex="end")
            if idx:
                line_end = self.chat.index(f"{idx} lineend")
                self.chat.delete(line_end, "end")
                self.chat.insert("end", "\n")
        self.chat.insert("end", piece, "ai")
        self.chat.see("end")
        self.chat.config(state="disabled")

    def _set_status(self, text, color=TEXT_DIM):
        self.status_label.config(text=text, fg=color)

    def _clear_chat(self):
        self.chat.config(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.config(state="disabled")

    def _check_deps(self):
        def check():
            missing = []
            try:
                import speech_recognition
            except ImportError:
                missing.append("SpeechRecognition")
            try:
                import ollama
            except ImportError:
                missing.append("ollama")
            if missing:
                self.after(0, lambda: self._append(
                    "error", f"缺少依赖：{', '.join(missing)}\n"
                             f"请运行：pip install {' '.join(missing)}"))
        threading.Thread(target=check, daemon=True).start()

    # ── 按住说话 ──
    def _mic_press(self, event):
        if self.listening:
            return
        self.listening = True
        self.mic_btn.config(bg=DANGER, text="🔴 录音中...")
        self._set_status("● 录音中", DANGER)
        threading.Thread(target=self._do_record, daemon=True).start()

    def _mic_release(self, event):
        self.listening = False

    def _do_record(self):
        try:
            text = record_and_recognize(timeout=8, phrase_limit=15)
            self.after(0, lambda: self.mic_btn.config(bg="#45475a", text="🎙 按住说话"))
            self.after(0, lambda: self._set_status("● 待机"))
            if text:
                self.after(0, lambda: self._handle_input(text))
            else:
                self.after(0, lambda: self._append("system", "未识别到语音，请重试"))
        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda: self.mic_btn.config(bg="#45475a", text="🎙 按住说话"))
            self.after(0, lambda: self._set_status("● 待机"))
            self.after(0, lambda msg=err_msg: self._append("error", f"录音失败：{msg}"))

    # ── 唤醒监听 ──
    def _toggle_wake(self):
        if self.wake_mode:
            self.wake_mode = False
            self.wake_btn.config(text="👂 开启唤醒监听", bg="#45475a")
            self._set_status("● 待机")
            self._append("system", "唤醒监听已关闭")
        else:
            self.wake_mode = True
            self.wake_btn.config(text="🟢 唤醒监听中", bg="#40a02b")
            self._set_status("● 监听唤醒词", ACCENT2)
            self._append("system", "唤醒监听已开启，说「小K」激活助手")
            threading.Thread(target=self._wake_loop, daemon=True).start()

    def _wake_loop(self):
        """持续监听唤醒词"""
        import speech_recognition as sr
        import sounddevice as sd
        r = sr.Recognizer()
        while self.wake_mode:
            try:
                audio = record_audio(duration=3)
                text = r.recognize_google(audio, language="zh-CN")
                text_lower = text.lower().replace(" ", "")
                if any(w.lower() in text_lower for w in WAKE_WORDS):
                    self.after(0, self._on_wake)
            except Exception:
                pass  # 超时或无声音，继续循环

    def _on_wake(self):
        """唤醒后录制指令"""
        self._append("system", "✨ 已唤醒，请说出指令...")
        self._set_status("● 等待指令", ACCENT)
        threading.Thread(target=self._listen_command, daemon=True).start()

    def _listen_command(self):
        try:
            text = record_and_recognize(timeout=6, phrase_limit=20)
            if text:
                self.after(0, lambda: self._handle_input(text))
            else:
                self.after(0, lambda: self._append("system", "未听清，请再说一次"))
                self.after(0, lambda: self._set_status("● 监听唤醒词", ACCENT2))
        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda msg=err_msg: self._append("error", f"识别失败：{msg}"))
            self.after(0, lambda: self._set_status("● 监听唤醒词", ACCENT2))

    # ── 文字输入 ──
    def _send_text(self):
        text = self.input_var.get().strip()
        if not text:
            return
        self.input_var.set("")
        self._handle_input(text)

    # ── 统一处理输入 ──
    def _handle_input(self, text):
        self._append("user", text)
        self._append("ai", "")  # 占位，流式填充
        self._set_status("● 处理中", ACCENT)

        def run():
            result = execute_command(
                text,
                log_fn=lambda m: self.after(0, lambda msg=m: self._append("system", msg)),
                stream_fn=lambda p, clear=False: self.after(
                    0, lambda piece=p, c=clear: self._stream_append(piece, c)))
            self.after(0, lambda: self._set_status(
                "● 监听唤醒词" if self.wake_mode else "● 待机",
                ACCENT2 if self.wake_mode else TEXT_DIM))
            # 如果 result 不是流式输出的内容，补充显示
            if result and not any(w in text for w in ["写", "生成", "帮我写", "创作"]):
                self.after(0, lambda r=result: self._stream_append(r, clear=True))
            self.after(0, lambda: self._append("system", ""))

        threading.Thread(target=run, daemon=True).start()


if __name__ == "__main__":
    app = VoiceAssistant()
    app.mainloop()
