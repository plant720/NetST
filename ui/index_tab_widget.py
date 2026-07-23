"""Localized academic Home tab for NetST."""

from PyQt6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget

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
        self._browser.document().setDocumentMargin(0)
        layout.addWidget(self._browser)
        self.update_language()

    def update_language(self) -> None:
        current_scroll = self._browser.verticalScrollBar().value()
        self._browser.setHtml(render_home(lang_manager.get_language()))
        self._browser.verticalScrollBar().setValue(current_scroll)
