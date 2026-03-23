#!/usr/bin/env python3
"""文件/文件夹说明查询 - 右键菜单调用"""

import os
import sys

# ── 文件夹说明库 ──────────────────────────────────────
FOLDER_DB = {
    # Windows 系统
    "windows":                  ("Windows 系统核心目录", "Microsoft / 系统", "danger"),
    "system32":                 ("64位系统核心DLL和驱动", "Microsoft / 系统", "danger"),
    "syswow64":                 ("32位兼容层系统文件", "Microsoft / 系统", "danger"),
    "winsxs":                   ("系统组件备份", "Microsoft / 系统", "danger"),
    "installer":                ("已安装程序缓存包", "Windows Installer", "danger"),
    "drivers":                  ("硬件驱动文件", "Microsoft / 驱动", "danger"),
    "recovery":                 ("系统恢复分区", "Microsoft / 系统", "danger"),
    "boot":                     ("系统启动文件", "Microsoft / 系统", "danger"),
    "system volume information":("系统还原点数据", "Microsoft / 系统", "danger"),
    "$recycle.bin":             ("回收站", "Windows 系统", "safe"),
    "prefetch":                 ("程序预读缓存，可清理", "Windows 系统", "safe"),
    "softwaredistribution":     ("Windows Update下载缓存，可清理", "Windows Update", "safe"),
    "temp":                     ("临时文件，可清理", "Windows 系统", "safe"),
    "fonts":                    ("系统字体文件", "Microsoft / 系统", "caution"),
    "windowspowershell":        ("PowerShell 脚本环境", "Microsoft / 系统", "danger"),
    "microsoft.net":            (".NET Framework 运行时", "Microsoft / .NET", "danger"),
    "msbuild":                  ("微软构建工具", "Microsoft / 开发", "caution"),
    "common files":             ("软件共享公共组件", "Microsoft / 多软件", "caution"),
    "reference assemblies":     (".NET 开发引用程序集", "Microsoft / 开发", "caution"),
    "windows nt":               ("Windows NT 系统组件", "Microsoft / 系统", "danger"),
    "windows media player":     ("Windows 媒体播放器", "Microsoft / 媒体", "caution"),
    "internet explorer":        ("IE浏览器（已停止支持）", "Microsoft / 浏览器", "caution"),
    "windowsapps":              ("UWP应用安装目录", "Microsoft / 应用商店", "danger"),
    "servicing":                ("系统服务组件更新", "Microsoft / 系统", "danger"),

    # Program Files 常见软件
    "google":                   ("Google 相关软件", "Google", "safe"),
    "chrome":                   ("Chrome 浏览器", "Google Chrome", "safe"),
    "mozilla firefox":          ("Firefox 浏览器", "Mozilla", "safe"),
    "microsoft office":         ("Office 办公套件", "Microsoft Office", "safe"),
    "wechat":                   ("微信 PC 版", "腾讯微信", "safe"),
    "tencent":                  ("腾讯系软件", "腾讯", "safe"),
    "qq":                       ("QQ 即时通讯", "腾讯QQ", "safe"),
    "netease":                  ("网易系软件", "网易", "safe"),
    "alibaba":                  ("阿里巴巴系软件", "阿里巴巴", "safe"),
    "dingtalk":                 ("钉钉办公软件", "阿里钉钉", "safe"),
    "bytedance":                ("字节跳动系软件", "字节跳动", "safe"),
    "feishu":                   ("飞书办公软件", "字节跳动", "safe"),
    "adobe":                    ("Adobe 创意软件套件", "Adobe", "safe"),
    "python":                   ("Python 运行环境", "Python", "caution"),
    "python311":                ("Python 3.11 运行环境", "Python", "caution"),
    "python312":                ("Python 3.12 运行环境", "Python", "caution"),
    "nodejs":                   ("Node.js 运行环境", "Node.js", "caution"),
    "java":                     ("Java 运行环境", "Oracle / OpenJDK", "caution"),
    "jdk":                      ("Java 开发工具包", "Oracle / OpenJDK", "caution"),
    "git":                      ("Git 版本控制工具", "Git", "caution"),
    "vscode":                   ("Visual Studio Code 编辑器", "Microsoft", "safe"),
    "visual studio":            ("Visual Studio 开发环境", "Microsoft", "safe"),
    "jetbrains":                ("JetBrains 系列 IDE", "JetBrains", "safe"),
    "steam":                    ("Steam 游戏平台", "Valve Steam", "safe"),
    "epic games":               ("Epic 游戏平台", "Epic Games", "safe"),
    "nvidia":                   ("NVIDIA 显卡驱动和工具", "NVIDIA", "caution"),
    "intel":                    ("Intel 硬件驱动和工具", "Intel", "caution"),
    "amd":                      ("AMD 硬件驱动和工具", "AMD", "caution"),
    "realtek":                  ("Realtek 声卡/网卡驱动", "Realtek", "caution"),
    "huawei":                   ("华为相关软件", "Huawei", "safe"),
    "edrawsoft":                ("亿图图示软件", "EdrawSoft", "safe"),
    "kugou":                    ("酷狗音乐", "酷狗", "safe"),
    "kugoumusic":               ("酷狗音乐数据", "酷狗", "safe"),
    "7-zip":                    ("7-Zip 压缩工具", "7-Zip", "safe"),
    "winrar":                   ("WinRAR 压缩工具", "WinRAR", "safe"),
    "potplayer":                ("PotPlayer 视频播放器", "Daum", "safe"),
    "vlc":                      ("VLC 媒体播放器", "VideoLAN", "safe"),
    "obs studio":               ("OBS 直播录屏软件", "OBS Project", "safe"),
    "zoom":                     ("Zoom 视频会议", "Zoom", "safe"),
    "ollama":                   ("Ollama 本地AI模型运行工具", "Ollama", "safe"),

    # AppData 子目录
    "local":                    ("本地应用数据，含缓存", "Windows 系统", "caution"),
    "roaming":                  ("漫游应用配置，软件设置", "Windows 系统", "caution"),
    "locallow":                 ("低权限应用数据", "Windows 系统", "caution"),
    "cache":                    ("缓存文件，可清理", "多软件通用", "safe"),
    "logs":                     ("日志文件，可清理", "多软件通用", "safe"),
    "crash reports":            ("程序崩溃报告，可删除", "多软件通用", "safe"),
    "updater":                  ("软件自动更新程序", "多软件通用", "caution"),
    "crashpad":                 ("程序崩溃收集器，可删除", "多软件通用", "safe"),

    # 开发目录
    "node_modules":             ("Node.js 依赖包，可重新安装", "Node.js / npm", "safe"),
    ".git":                     ("Git 版本控制数据", "Git", "caution"),
    "dist":                     ("项目构建输出目录", "开发工具", "safe"),
    "build":                    ("项目构建目录", "开发工具", "safe"),
    ".vscode":                  ("VS Code 项目配置", "VS Code", "safe"),
    ".idea":                    ("JetBrains IDE 项目配置", "JetBrains", "safe"),
    "venv":                     ("Python 虚拟环境", "Python", "safe"),
    "__pycache__":              ("Python 编译缓存，可删除", "Python", "safe"),

    # 用户目录
    "desktop":                  ("桌面文件", "Windows 系统", "safe"),
    "documents":                ("我的文档", "Windows 系统", "safe"),
    "downloads":                ("下载文件夹", "Windows 系统", "safe"),
    "pictures":                 ("图片文件夹", "Windows 系统", "safe"),
    "videos":                   ("视频文件夹", "Windows 系统", "safe"),
    "music":                    ("音乐文件夹", "Windows 系统", "safe"),
    "appdata":                  ("应用程序用户数据", "Windows 系统", "caution"),
    "programdata":              ("应用程序公共数据", "Windows 系统", "caution"),
}

# ── 文件说明库 ────────────────────────────────────────
FILE_DB = {
    # 按文件名精确匹配
    "pagefile.sys":     ("Windows 虚拟内存页面文件", "Windows 系统", "danger"),
    "hiberfil.sys":     ("休眠文件，关闭休眠可删", "Windows 系统", "caution"),
    "swapfile.sys":     ("现代应用虚拟内存", "Windows 系统", "danger"),
    "ntldr":            ("Windows XP 启动加载器", "Windows 系统", "danger"),
    "bootmgr":          ("Windows 启动管理器", "Windows 系统", "danger"),
    "ntoskrnl.exe":     ("Windows 内核文件，系统核心", "Windows 系统", "danger"),
    "lsass.exe":        ("本地安全认证进程，管理登录", "Windows 系统", "danger"),
    "svchost.exe":      ("服务宿主进程，承载多个系统服务", "Windows 系统", "danger"),
    "explorer.exe":     ("Windows 资源管理器（桌面和文件浏览）", "Windows 系统", "danger"),
    "csrss.exe":        ("客户端/服务器运行时子系统", "Windows 系统", "danger"),
    "winlogon.exe":     ("Windows 登录管理进程", "Windows 系统", "danger"),
    "taskmgr.exe":      ("任务管理器", "Windows 系统", "caution"),
    "regedit.exe":      ("注册表编辑器", "Windows 系统", "caution"),
    "cmd.exe":          ("命令提示符", "Windows 系统", "caution"),
    "powershell.exe":   ("PowerShell 脚本环境", "Windows 系统", "caution"),
    "msiexec.exe":      ("Windows 安装程序引擎", "Windows Installer", "caution"),
    "desktop.ini":      ("文件夹显示配置，系统隐藏文件", "Windows 系统", "caution"),
    "thumbs.db":        ("缩略图缓存，可删除", "Windows 系统", "safe"),
    "package.json":     ("Node.js 项目配置和依赖声明", "Node.js / npm", "caution"),
    "package-lock.json":("npm 依赖锁定文件", "npm", "caution"),
    "yarn.lock":        ("Yarn 依赖锁定文件", "Yarn", "caution"),
    "pom.xml":          ("Maven 项目配置文件", "Java / Maven", "caution"),
    "build.gradle":     ("Gradle 构建配置文件", "Java / Gradle", "caution"),
    "requirements.txt": ("Python 依赖列表", "Python / pip", "caution"),
    "dockerfile":       ("Docker 镜像构建文件", "Docker", "caution"),
    "docker-compose.yml":("Docker 多容器编排配置", "Docker", "caution"),
    ".env":             ("环境变量配置，可能含密钥，勿泄露", "通用", "caution"),
    ".gitignore":       ("Git 忽略规则文件", "Git", "safe"),
    "readme.md":        ("项目说明文档", "通用", "safe"),
    "license":          ("开源许可证文件", "通用", "safe"),
    "makefile":         ("Make 构建脚本", "Make / 开发", "caution"),
}

# ── 扩展名说明库 ──────────────────────────────────────
EXT_DB = {
    # 系统核心
    ".dll":     ("动态链接库，程序运行依赖的共享代码", "Windows 系统 / 各软件", "danger"),
    ".sys":     ("系统驱动文件", "Windows 系统", "danger"),
    ".drv":     ("硬件驱动程序", "Windows 系统", "danger"),
    ".ocx":     ("ActiveX 控件组件", "Windows 系统", "danger"),
    ".cpl":     ("控制面板扩展", "Windows 系统", "danger"),
    ".msc":     ("微软管理控制台文件", "Windows 系统", "caution"),
    ".cat":     ("安全目录，验证驱动签名", "Windows 系统", "caution"),
    ".manifest":("程序清单，描述程序依赖", "Windows 系统", "caution"),
    ".mui":     ("多语言界面资源文件", "Windows 系统", "caution"),
    ".inf":     ("设备驱动安装信息", "Windows 系统", "caution"),

    # 可执行
    ".exe":     ("可执行程序", "各软件", "caution"),
    ".msi":     ("Windows 安装包", "Windows Installer", "caution"),
    ".bat":     ("批处理脚本", "Windows 系统", "caution"),
    ".cmd":     ("命令脚本", "Windows 系统", "caution"),
    ".ps1":     ("PowerShell 脚本", "PowerShell", "caution"),
    ".vbs":     ("VBScript 脚本", "Windows 系统", "caution"),
    ".sh":      ("Shell 脚本（Linux/Mac）", "Unix/Linux", "caution"),

    # 配置
    ".reg":     ("注册表文件，双击会修改注册表", "Windows 系统", "caution"),
    ".ini":     ("程序配置文件", "各软件", "caution"),
    ".cfg":     ("程序配置文件", "各软件", "caution"),
    ".conf":    ("程序配置文件", "各软件", "caution"),
    ".xml":     ("XML 配置/数据文件", "通用", "caution"),
    ".json":    ("JSON 数据/配置文件", "通用", "safe"),
    ".yaml":    ("YAML 配置文件", "通用", "caution"),
    ".yml":     ("YAML 配置文件", "通用", "caution"),
    ".toml":    ("TOML 配置文件", "通用", "caution"),
    ".env":     ("环境变量配置，可能含密钥", "通用", "caution"),

    # 可清理
    ".tmp":     ("临时文件，可安全删除", "系统/各软件", "safe"),
    ".log":     ("日志文件，通常可删除", "系统/各软件", "safe"),
    ".bak":     ("备份文件，确认无用后可删除", "各软件", "safe"),
    ".old":     ("旧版本文件，通常可删除", "各软件", "safe"),
    ".dmp":     ("程序崩溃转储文件，可删除", "Windows 系统", "safe"),
    ".crdownload":("Chrome 未完成下载，可删除", "Chrome", "safe"),
    ".part":    ("未完成下载文件，可删除", "下载工具", "safe"),
    ".partial": ("未完成下载文件，可删除", "下载工具", "safe"),
    ".cache":   ("缓存文件，可清理", "各软件", "safe"),
    "~":        ("临时备份文件，可删除", "各软件", "safe"),

    # 文档
    ".pdf":     ("PDF 文档", "Adobe / 通用", "safe"),
    ".doc":     ("Word 文档（旧格式）", "Microsoft Word", "safe"),
    ".docx":    ("Word 文档", "Microsoft Word", "safe"),
    ".xls":     ("Excel 表格（旧格式）", "Microsoft Excel", "safe"),
    ".xlsx":    ("Excel 表格", "Microsoft Excel", "safe"),
    ".ppt":     ("PowerPoint 演示（旧格式）", "Microsoft PowerPoint", "safe"),
    ".pptx":    ("PowerPoint 演示文稿", "Microsoft PowerPoint", "safe"),
    ".txt":     ("纯文本文件", "通用", "safe"),
    ".md":      ("Markdown 文档", "通用", "safe"),
    ".csv":     ("逗号分隔值，表格数据", "通用", "safe"),
    ".rtf":     ("富文本格式文档", "通用", "safe"),

    # 图片
    ".jpg":     ("JPEG 图片", "通用", "safe"),
    ".jpeg":    ("JPEG 图片", "通用", "safe"),
    ".png":     ("PNG 图片（支持透明）", "通用", "safe"),
    ".gif":     ("GIF 动图", "通用", "safe"),
    ".bmp":     ("位图图片", "通用", "safe"),
    ".ico":     ("图标文件", "Windows 系统 / 各软件", "caution"),
    ".svg":     ("矢量图形", "通用", "safe"),
    ".webp":    ("WebP 图片（Google格式）", "Google", "safe"),
    ".psd":     ("Photoshop 源文件", "Adobe Photoshop", "safe"),
    ".ai":      ("Illustrator 源文件", "Adobe Illustrator", "safe"),
    ".raw":     ("相机原始图像数据", "相机/图像软件", "safe"),

    # 视频
    ".mp4":     ("MP4 视频", "通用", "safe"),
    ".avi":     ("AVI 视频", "通用", "safe"),
    ".mkv":     ("MKV 视频（高清常用）", "通用", "safe"),
    ".mov":     ("QuickTime 视频", "Apple", "safe"),
    ".wmv":     ("Windows 媒体视频", "Microsoft", "safe"),
    ".flv":     ("Flash 视频（已淘汰）", "Adobe Flash", "safe"),
    ".webm":    ("WebM 网页视频", "Google", "safe"),

    # 音频
    ".mp3":     ("MP3 音频", "通用", "safe"),
    ".wav":     ("WAV 无损音频", "通用", "safe"),
    ".flac":    ("FLAC 无损压缩音频", "通用", "safe"),
    ".aac":     ("AAC 音频", "通用", "safe"),
    ".ogg":     ("OGG 开源音频格式", "通用", "safe"),
    ".wma":     ("Windows 媒体音频", "Microsoft", "safe"),

    # 压缩
    ".zip":     ("ZIP 压缩包", "通用", "safe"),
    ".rar":     ("RAR 压缩包", "WinRAR", "safe"),
    ".7z":      ("7-Zip 压缩包", "7-Zip", "safe"),
    ".tar":     ("TAR 打包文件（Linux常用）", "Unix/Linux", "safe"),
    ".gz":      ("GZip 压缩文件", "Unix/Linux", "safe"),
    ".iso":     ("光盘镜像文件", "通用", "caution"),

    # 开发
    ".py":      ("Python 脚本", "Python", "safe"),
    ".pyc":     ("Python 编译缓存，可删除", "Python", "safe"),
    ".js":      ("JavaScript 脚本", "Node.js / 浏览器", "safe"),
    ".ts":      ("TypeScript 脚本", "TypeScript", "safe"),
    ".html":    ("网页文件", "浏览器", "safe"),
    ".css":     ("网页样式文件", "浏览器", "safe"),
    ".java":    ("Java 源代码", "Java", "safe"),
    ".class":   ("Java 编译字节码", "Java", "safe"),
    ".jar":     ("Java 可执行包", "Java", "caution"),
    ".cpp":     ("C++ 源代码", "C++", "safe"),
    ".c":       ("C 语言源代码", "C", "safe"),
    ".h":       ("C/C++ 头文件", "C/C++", "safe"),
    ".cs":      ("C# 源代码", "Microsoft C#", "safe"),
    ".go":      ("Go 语言源代码", "Go", "safe"),
    ".rs":      ("Rust 源代码", "Rust", "safe"),
    ".php":     ("PHP 脚本", "PHP", "safe"),
    ".sql":     ("SQL 数据库脚本", "数据库", "caution"),
    ".db":      ("数据库文件", "各数据库软件", "caution"),
    ".sqlite":  ("SQLite 数据库文件", "SQLite", "caution"),

    # 快捷方式
    ".lnk":     ("Windows 快捷方式", "Windows 系统", "safe"),
    ".url":     ("网页快捷方式", "Windows 系统", "safe"),

    # 字体
    ".ttf":     ("TrueType 字体文件", "Windows 系统 / 通用", "caution"),
    ".otf":     ("OpenType 字体文件", "Windows 系统 / 通用", "caution"),
    ".woff":    ("网页字体文件", "浏览器", "safe"),
}

RISK_LABEL = {
    "safe":    "✓ 可安全删除",
    "caution": "⚠ 谨慎操作",
    "danger":  "✗ 禁止删除",
}


def ask_ai(filename, filepath, is_dir):
    try:
        import ollama
        kind = "文件夹" if is_dir else "文件"
        prompt = (
            f"我在 Windows 电脑上看到一个{kind}，请用中文简短回答：\n"
            f"1. 这个{kind}是做什么的？\n"
            f"2. 与哪些软件或系统功能相关？\n"
            f"3. 可以删除吗？\n\n"
            f"{kind}名：{filename}\n路径：{filepath}\n\n"
            f"控制在80字以内，直接回答。"
        )
        resp = ollama.chat(
            model="qwen2.5:7b",
            messages=[{"role": "user", "content": prompt}]
        )
        return resp["message"]["content"].strip()
    except Exception as e:
        return f"AI 分析失败: {e}\n（本地知识库中无此文件记录）"


def query(path):
    import ctypes
    path = path.strip().strip('"')
    name = os.path.basename(path).lower()
    ext  = os.path.splitext(name)[1].lower()

    icons = {"safe": 0x40, "caution": 0x30, "danger": 0x10}

    if os.path.isdir(path):
        if name in FOLDER_DB:
            desc, related, risk = FOLDER_DB[name]
            msg = f"文件夹: {os.path.basename(path)}\n路径: {path}\n\n说明: {desc}\n相关: {related}\n风险: {RISK_LABEL[risk]}"
            ctypes.windll.user32.MessageBoxW(0, msg, "文件说明", icons[risk])
        else:
            ai = ask_ai(os.path.basename(path), path, True)
            ctypes.windll.user32.MessageBoxW(0, f"文件夹: {os.path.basename(path)}\n路径: {path}\n\n🤖 AI 分析：\n{ai}", "文件说明 (AI)", 0x40)
    else:
        if name in FILE_DB:
            desc, related, risk = FILE_DB[name]
        elif ext in EXT_DB:
            desc, related, risk = EXT_DB[ext]
        else:
            ai = ask_ai(os.path.basename(path), path, False)
            ctypes.windll.user32.MessageBoxW(0, f"文件: {os.path.basename(path)}\n路径: {path}\n\n🤖 AI 分析：\n{ai}", "文件说明 (AI)", 0x40)
            return
        msg = f"文件: {os.path.basename(path)}\n路径: {path}\n\n说明: {desc}\n相关: {related}\n风险: {RISK_LABEL[risk]}"
        ctypes.windll.user32.MessageBoxW(0, msg, "文件说明", icons[risk])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, "请通过右键菜单使用此工具", "文件说明", 0x40)
    else:
        query(sys.argv[1])
