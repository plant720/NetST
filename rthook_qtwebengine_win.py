# !/usr/bin/env python
# -*- coding: utf-8 -*-
# rthook_qtwebengine_win.py
# PyInstaller onefile 运行时钩子（Windows）
# 修正 QtWebEngineProcess.exe 及相关资源路径，使 QWebEngineView 能在打包后正常运行。

import os
import sys

if getattr(sys, 'frozen', False):
    base = sys._MEIPASS

    # QtWebEngineProcess.exe 位于 PyQt6/Qt6/bin/
    process_exe = os.path.join(base, 'PyQt6', 'Qt6', 'bin', 'QtWebEngineProcess.exe')
    if os.path.isfile(process_exe):
        os.environ.setdefault('QTWEBENGINEPROCESS_PATH', process_exe)

    # QtWebEngine 资源目录（qtwebengine_resources.pak 等）
    resources_dir = os.path.join(base, 'PyQt6', 'Qt6', 'resources')
    if os.path.isdir(resources_dir):
        os.environ.setdefault('QTWEBENGINE_RESOURCES_PATH', resources_dir)

    # 本地化文件目录（.pak 语言包）
    locales_dir = os.path.join(base, 'PyQt6', 'Qt6', 'translations', 'qtwebengine_locales')
    if os.path.isdir(locales_dir):
        os.environ.setdefault('QTWEBENGINE_LOCALES_PATH', locales_dir)
