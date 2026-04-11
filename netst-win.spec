# -*- mode: python ; coding: utf-8 -*-
# netst-win.spec - PyInstaller Windows 打包配置文件（单文件模式）
# 用法: pyinstaller netst-win.spec --noconfirm
# 输出: dist/NetST.exe（单个可执行文件，所有资源内嵌）

from PyInstaller.utils.hooks import collect_all

# ======================== 资源与依赖配置 ========================
# 非代码资源：static(图标/样式等), lib/win(Windows 专用外部库)
datas = [('static', 'static'), ('lib/win', 'lib/win')]
binaries = []
hiddenimports = []

# 收集 PyQt6 全部资源（含 QtWebEngine 的 framework 和 resources）
tmp_ret = collect_all('PyQt6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# ======================== 分析阶段 ========================
a = Analysis(
    ['main_form.py'],                           # 主程序入口
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['rthook_qtwebengine_win.py'], # 运行时钩子：修正 QtWebEngine 路径
    excludes=[                                   # 排除不需要的 PyQt6 子模块（减小体积）
        'PyQt6.Qt3DCore', 'PyQt6.Qt3DRender', 'PyQt6.QtBluetooth',
        'PyQt6.QtNfc', 'PyQt6.QtSensors', 'PyQt6.QtSerialPort',
        'PyQt6.QtSql', 'PyQt6.QtTest', 'PyQt6.QtRemoteObjects',
        'PyQt6.QtQuick3D', 'PyQt6.QtTextToSpeech',
    ],
    noarchive=False,
    optimize=0,
)

# ======================== 打包阶段（单文件模式）========================
pyz = PYZ(a.pure)

# onefile 模式：将 binaries 和 datas 直接传入 EXE，不使用 COLLECT
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,                                  # 内嵌所有二进制依赖
    a.datas,                                     # 内嵌所有数据资源
    name='NetST',                                # 输出文件名：NetST.exe
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,                               # GUI 应用，不显示终端窗口
    argv_emulation=False,
    target_arch=None,                            # None = 自动检测架构（intel/arm）
    codesign_identity=None,
    entitlements_file=None,
    icon=['static/icon/netst.ico'],              # Windows 应用图标
)
