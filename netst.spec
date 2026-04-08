# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller build specification for NetST.

Usage (from the project root):
    pip install pyinstaller
    pyinstaller netst.spec --clean

Output:
    dist/NetST/          – directory distribution (all platforms)
    dist/NetST.app       – macOS app bundle (macOS only)
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files

IS_WINDOWS = sys.platform.startswith('win')
IS_MAC     = sys.platform == 'darwin'

# Target architecture:
#   macOS  – native arm64 Python (no Rosetta)
#   Windows – native x86_64 Python
if IS_MAC:
    _target_arch = 'arm64'
elif IS_WINDOWS:
    _target_arch = 'x86_64'
else:
    _target_arch = None   # Linux: let PyInstaller detect

# ── Data files bundled alongside the executable ──────────────────────────────
datas = [
    ('statics', 'statics'),   # icon, web assets (tcsbu), docs
    ('lib',     'lib'),       # external binaries: fastHaN, muscle3, mafft-*
]

# PyQt6-WebEngine ships locale / pak / resources that must be present at runtime
for _pkg in ('PyQt6.QtWebEngineWidgets', 'PyQt6.QtWebEngineCore'):
    try:
        datas += collect_data_files(_pkg)
    except Exception:
        pass

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    ['main_form.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # PyQt6 modules that are imported dynamically
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebChannel',
        'PyQt6.QtPrintSupport',
        'PyQt6.sip',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

# ── Platform icon ─────────────────────────────────────────────────────────────
if IS_WINDOWS:
    _icon = os.path.join('statics', 'icon', 'netst.ico')
elif IS_MAC:
    # macOS prefers .icns; fall back to .ico when .icns is not available
    _icns = os.path.join('statics', 'icon', 'netst.icns')
    _icon = _icns if os.path.isfile(_icns) else os.path.join('statics', 'icon', 'netst.ico')
else:
    _icon = None

# ── Executable ────────────────────────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NetST',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,       # No terminal window (GUI app)
    argv_emulation=False,
    target_arch=_target_arch,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon,
)

# ── Directory distribution (--onedir) ────────────────────────────────────────
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    # Do not compress external tool binaries or Qt libs (breaks them or gives no benefit)
    upx_exclude=['fastHaN*', 'muscle*', 'mafft*', 'Qt*', '*.dylib', '*.so'],
    name='NetST',
)

# ── macOS App Bundle ──────────────────────────────────────────────────────────
if IS_MAC:
    app = BUNDLE(
        coll,
        name='NetST.app',
        icon=_icon,
        bundle_identifier='com.netst.haplotype',
        info_plist={
            'CFBundleShortVersionString': '1.0.0',
            'NSHighResolutionCapable': True,
            'LSBackgroundOnly': False,
            'NSRequiresAquaSystemAppearance': False,
        },
    )
