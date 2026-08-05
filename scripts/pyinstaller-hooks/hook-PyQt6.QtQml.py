"""Collect QtQml's native dependencies without the unused QML module tree.

NetST uses QtWebEngineWidgets, whose native libraries depend on QtQml and
QtQuick. It does not load QML documents. PyInstaller's stock QtQml hook copies
every installed QML module, including Quick 3D, multimedia, controls, and style
plugins; those files are not required by the widget-based application.
"""

from PyInstaller.utils.hooks.qt import add_qt6_dependencies


hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
