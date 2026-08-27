"""Localized academic Home tab for NetST."""

import os
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget

from service.resource_path import application_root

from .home_content import render_home
from .language_manager import lang_manager


class IndexTabWidget(QWidget):
    """Academic software overview that can be re-rendered in either language."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._browser = QTextBrowser()
        self._browser.setReadOnly(True)
        self._browser.setOpenExternalLinks(True)
        self._browser.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._browser.document().setDocumentMargin(0)
        image_root = Path(application_root()) / "statics" / "fig"
        self._image_base_url = QUrl.fromLocalFile(
            str(image_root.resolve()) + os.sep
        )
        self._browser.document().setBaseUrl(self._image_base_url)

        self._last_viewport_width = 0
        self._last_language = ""
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(100)
        self._resize_timer.timeout.connect(self._render_home)

        layout.addWidget(self._browser)
        self.update_language()

    def update_language(self) -> None:
        self._render_home(force=True)

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt API)
        super().resizeEvent(event)
        self._resize_timer.start()

    def _render_home(self, force: bool = False) -> None:
        language = lang_manager.get_language()
        viewport_width = max(self._browser.viewport().width(), 320)
        if (
            not force
            and language == self._last_language
            and abs(viewport_width - self._last_viewport_width) < 8
        ):
            return

        current_scroll = self._browser.verticalScrollBar().value()
        self._browser.document().setBaseUrl(self._image_base_url)
        self._browser.setHtml(render_home(language, viewport_width))
        self._last_language = language
        self._last_viewport_width = viewport_width
        QTimer.singleShot(0, lambda: self._restore_scroll(current_scroll))

    def _restore_scroll(self, value: int) -> None:
        scroll_bar = self._browser.verticalScrollBar()
        scroll_bar.setValue(min(value, scroll_bar.maximum()))
