# -*- mode: python ; coding: utf-8 -*-
# netst-win.spec - PyInstaller Windows 打包配置文件
# 用法: pyinstaller netst-win.spec --noconfirm
# 输出: dist/NetST/ 目录（含 NetST.exe）

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
    ['main_form.py'],                       # 主程序入口
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],                       # Windows 无需 QtWebEngine 路径修正钩子
    excludes=[                              # 排除不需要的 PyQt6 子模块（减小体积）
        'PyQt6.Qt3DCore', 'PyQt6.Qt3DRender', 'PyQt6.QtBluetooth',
        'PyQt6.QtNfc', 'PyQt6.QtSensors', 'PyQt6.QtSerialPort',
        'PyQt6.QtSql', 'PyQt6.QtTest', 'PyQt6.QtRemoteObjects',
        'PyQt6.QtQuick3D', 'PyQt6.QtTextToSpeech',
    ],
    noarchive=False,
    optimize=0,
)

# ======================== 打包阶段 ========================
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NetST',                           # 可执行文件名（NetST.exe）
    debug=False,
    strip=False,
    upx=True,
    console=False,                          # GUI 应用，不显示终端窗口
    argv_emulation=False,
    target_arch=None,                       # None = 自动检测架构（intel/arm）
    codesign_identity=None,
    entitlements_file=None,
    icon=['static/icon/netst.ico'],         # Windows 应用图标
)

# 将可执行文件与资源收集到 dist/NetST/ 目录
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NetST',
)
