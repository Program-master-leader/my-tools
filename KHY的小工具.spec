# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['gui_center.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('tools.json', '.'),
    ],
    hiddenimports=['tkinter', 'tkinter.ttk', 'tkinter.messagebox',
                   'tkinter.simpledialog', 'tkinter.filedialog',
                   'winreg', 'json', 'subprocess', 'threading',
                   'urllib.request', 'webbrowser',
                   'watchdog', 'watchdog.observers', 'watchdog.events',
                   'watchdog.observers.winapi'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='KHY的小工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # 无黑框
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
