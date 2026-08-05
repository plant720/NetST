# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build for 64-bit Windows, with onedir and optional onefile."""

import os
import platform
import struct
import sys


if not sys.platform.startswith("win") or struct.calcsize("P") != 8:
    raise SystemExit("netst-win.spec must be built with 64-bit Python on Windows")
if platform.machine().lower() not in {"amd64", "x86_64"}:
    raise SystemExit("The supported Windows release target is x86-64")

onefile = os.environ.get("NETST_ONEFILE", "0") == "1"

# PyInstaller's official PyQt6 WebEngine hook supplies QtWebEngineProcess.exe,
# resources and locales. Directory mode is recommended because this project
# also ships a large MAFFT tree and does not need to extract it on every start.
datas = [
    ("static/docs", "static/docs"),
    ("static/tcsbu", "static/tcsbu"),
    ("lib/win", "lib/win"),
]

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
    "_hashlib", "_ssl", "ssl", "ftplib", "http.client",
    "http.cookiejar", "urllib.request", "xml.sax",
    # Stdlib modules not used at runtime.
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

# NetST uses WebEngine only for the bundled local tcsBU page. Remove browser
# locales and optional Qt plug-ins, along with their QtPdf/QtSerialPort DLL
# dependencies, from the release payload.
def keep_release_entry(entry):
    fields = "/".join(str(value) for value in entry[:2]).replace("\\", "/")
    lowered = fields.lower()
    if "/qtwebengine_locales/" in lowered:
        return False
    if "/pyqt6/qt6/translations/" in lowered:
        return False
    if "qtwebengine_devtools_resources.pak" in lowered:
        return False
    if "/plugins/imageformats/qpdf.dll" in lowered:
        return False
    if "/plugins/position/qtposition_nmea.dll" in lowered:
        return False
    if "qt6pdf.dll" in lowered or "qt6serialport.dll" in lowered:
        return False
    filename = os.path.basename(entry[0]).lower()
    if filename.endswith(".dll") and (
        filename.startswith("libcrypto") or filename.startswith("libssl")
    ):
        return False
    unused_plugin_dirs = (
        "/plugins/generic/", "/plugins/iconengines/", "/plugins/imageformats/",
        "/plugins/multimedia/", "/plugins/networkinformation/",
        "/plugins/position/", "/plugins/styles/", "/plugins/tls/",
    )
    if any(directory in lowered for directory in unused_plugin_dirs):
        return False
    if "/plugins/platforms/qminimal.dll" in lowered:
        return False
    return True


a.binaries = [entry for entry in a.binaries if keep_release_entry(entry)]
a.datas = [entry for entry in a.datas if keep_release_entry(entry)]

pyz = PYZ(a.pure)

if onefile:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name="NetST",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        icon="static/icon/netst.ico",
    )
else:
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
        icon="static/icon/netst.ico",
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        name="NetST",
    )
