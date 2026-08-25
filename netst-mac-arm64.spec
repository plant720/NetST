# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build for the native Apple Silicon NetST application."""

import os
import platform
import sys


if sys.platform != "darwin" or platform.machine().lower() not in {"arm64", "aarch64"}:
    raise SystemExit("netst-mac-arm64.spec must be built on Apple Silicon macOS")

# The version is provided by scripts/build.py through NETST_VERSION (its
# --version argument). No version number is hardcoded anywhere in the tree.
version = os.environ.get("NETST_VERSION")
if not version:
    raise SystemExit(
        "NETST_VERSION is not set. Build through scripts/build.py --version X.Y.Z"
    )
codesign_identity = os.environ.get("NETST_CODESIGN_IDENTITY") or None
entitlements_file = os.environ.get("NETST_ENTITLEMENTS_FILE") or None

# PyInstaller's official PyQt6 WebEngine hook collects the helper application,
# frameworks, resources and locales. Do not collect all of PyQt6: doing so adds
# unused QML/modules and can more than double the application size.
datas = [
    ("static/docs", "static/docs"),
    ("static/tcsbu", "static/tcsbu"),
    ("lib/mac_arm64", "lib/mac_arm64"),
]

# Bindings that NetST never imports. The QtWebEngine native libraries still
# retain their linked Qt frameworks (Qml, Quick, OpenGL, Positioning, DBus), but
# their unused Python wrappers and hooks do not need to be packaged.
unused_modules = [
    "PyQt6.Qt3DCore", "PyQt6.Qt3DRender", "PyQt6.QtBluetooth",
    "PyQt6.QtDBus", "PyQt6.QtDesigner", "PyQt6.QtHelp",
    "PyQt6.QtMultimedia", "PyQt6.QtMultimediaWidgets",
    "PyQt6.QtNfc", "PyQt6.QtOpenGL",
    "PyQt6.QtPositioning", "PyQt6.QtQml", "PyQt6.QtQuick",
    "PyQt6.QtQuick3D", "PyQt6.QtQuickWidgets", "PyQt6.QtRemoteObjects",
    "PyQt6.QtSensors", "PyQt6.QtSerialPort", "PyQt6.QtSql",
    "PyQt6.QtSvgWidgets", "PyQt6.QtTest", "PyQt6.QtTextToSpeech",
    "PyQt6.QtXml",
    # Pulled in indirectly by the stdlib XML hook. NetST has no Python network
    # client and hashlib falls back to Python's built-in SHA implementations.
    "_hashlib", "_ssl", "ssl", "ftplib", "http.client",
    "http.cookiejar", "urllib.request", "xml.sax",
    # Stdlib modules that PyInstaller's dependency walker pulls in but the
    # application never imports at runtime.
    "asyncio", "concurrent", "email", "http.server",
    "imaplib", "lzma", "multiprocessing", "nntplib", "pdb",
    "poplib", "pydoc", "smtplib", "socketserver",
    "sqlite3", "unittest", "webbrowser", "xmlrpc",
]

a = Analysis(
    ["main_form.py"],
    pathex=[SPECPATH],
    binaries=[],
    datas=datas,
    hiddenimports=["PyQt6.QtWebEngineWidgets"],
    hookspath=["scripts/pyinstaller-hooks"],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PyQt5", "PySide2", "PySide6", "tkinter", "numpy",
        *unused_modules,
    ],
    noarchive=False,
    optimize=0,
)

# NetST uses WebEngine only for a bundled local JavaScript page. Remove browser
# locales and optional Qt payloads after dependency analysis; the linked
# WebEngine libraries, helper process, ICU data, and core resource pack remain.
def keep_release_entry(entry):
    fields = "/".join(str(value) for value in entry[:2]).replace("\\", "/")
    lowered = fields.lower()
    if "/qtwebengine_locales/" in lowered:
        return False
    if "/pyqt6/qt6/translations/" in lowered:
        return False
    if "qtwebengine_devtools_resources.pak" in lowered:
        return False
    if "/plugins/imageformats/libqpdf.dylib" in lowered:
        return False
    if "/plugins/position/libqtposition_nmea.dylib" in lowered:
        return False
    if "qtpdf.framework" in lowered or "qtserialport.framework" in lowered:
        return False
    if os.path.basename(entry[0]).lower() in {"libcrypto.3.dylib", "libssl.3.dylib"}:
        return False
    unused_plugin_dirs = (
        "/plugins/generic/", "/plugins/iconengines/", "/plugins/imageformats/",
        "/plugins/multimedia/", "/plugins/networkinformation/",
        "/plugins/position/", "/plugins/styles/", "/plugins/tls/",
    )
    if any(directory in lowered for directory in unused_plugin_dirs):
        return False
    if "/plugins/platforms/libqminimal.dylib" in lowered:
        return False
    return True


a.binaries = [entry for entry in a.binaries if keep_release_entry(entry)]
a.datas = [entry for entry in a.datas if keep_release_entry(entry)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="NetST",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    argv_emulation=False,
    target_arch="arm64",
    codesign_identity=codesign_identity,
    entitlements_file=entitlements_file,
    icon="static/icon/netst.icns",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="NetST",
)

app = BUNDLE(
    coll,
    name="NetST.app",
    icon="static/icon/netst.icns",
    bundle_identifier="com.netst.app",
    version=version,
    info_plist={
        "CFBundleDisplayName": "NetST",
        "CFBundleShortVersionString": version,
        "CFBundleVersion": version,
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
    },
)
