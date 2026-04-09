# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2026/4/8 19:57
# @Author     : zzhen
# @File       : rthook_qtwebengine.py
# @Software   : PyCharm
# @Description: 
# @Copyright  : Copyright (c) 2026 by zzhen, All Rights Reserved.

import os
import sys

if getattr(sys, 'frozen', False):
    base = sys._MEIPASS
    fw = os.path.join(base, 'PyQt6', 'Qt6', 'lib',
                      'QtWebEngineCore.framework', 'Versions', 'Resources')
    os.environ['QTWEBENGINEPROCESS_PATH'] = os.path.join(
        fw, 'Helpers', 'QtWebEngineProcess.app', 'Contents', 'MacOS', 'QtWebEngineProcess')
    os.environ['QTWEBENGINE_RESOURCES_PATH'] = os.path.join(fw, 'Resources')
    os.environ['QTWEBENGINE_LOCALES_PATH'] = os.path.join(fw, 'Resources', 'qtwebengine_locales')
