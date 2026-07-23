"""
Status Bar Widget Module

Provides the status bar component with status message and progress bar.
"""

from typing import Callable, Optional

from PyQt6.QtWidgets import QProgressBar, QLabel, QPushButton

from .language_manager import lang_manager


class StatusBarWidget:
    """
    Status Bar Widget Class
    
    Manages the status bar with status message display and progress bar.
    """

    def __init__(self, parent):
        """Initialize the status bar widget"""
        self.parent = parent
        self.status_bar = parent.statusBar()

        self.status_label = None
        self.progress_bar = None
        self.cancel_button = None
        self._cancel_callback: Optional[Callable[[], None]] = None
        self._status_key: Optional[str] = 'status_ready'

        self._setup_ui()

    def _setup_ui(self):
        """Setup user interface"""
        # Status label
        self.status_label = QLabel(lang_manager.get('status_ready', 'Ready'))
        self.status_bar.addWidget(self.status_label, 1)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

        self.cancel_button = QPushButton(lang_manager.get('btn_cancel', 'Cancel'))
        self.cancel_button.setVisible(False)
        self.cancel_button.clicked.connect(self._cancel)
        self.status_bar.addPermanentWidget(self.cancel_button)

    def set_status_key(self, key: str, default: str = '') -> None:
        self._status_key = key
        self.status_label.setText(lang_manager.get(key, default))

    def set_progress(self, value: int):
        """Set progress bar value (0-100)"""
        if value > 0:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(value)
        else:
            self.progress_bar.setVisible(False)
            self.progress_bar.setValue(0)

    def set_cancel_callback(self, callback: Optional[Callable[[], None]]) -> None:
        """Show a cancel action while a cancellable task is active."""
        self._cancel_callback = callback
        self.cancel_button.setVisible(callback is not None)
        self.cancel_button.setEnabled(callback is not None)

    def _cancel(self) -> None:
        if self._cancel_callback is None:
            return
        self.cancel_button.setEnabled(False)
        self.set_status_key('status_cancelling', 'Cancelling...')
        self._cancel_callback()

    def update_language(self) -> None:
        self.cancel_button.setText(lang_manager.get('btn_cancel', 'Cancel'))
        if self._status_key:
            self.status_label.setText(lang_manager.get(self._status_key))
