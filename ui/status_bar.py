"""
Status Bar Widget Module

Provides the status bar component with status message and progress bar.
"""

from PyQt6.QtWidgets import QStatusBar, QProgressBar, QLabel
from PyQt6.QtCore import Qt


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
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup user interface"""
        # Status label
        self.status_label = QLabel("Ready")
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
    
    def set_status(self, message: str):
        """Set status message"""
        self.status_label.setText(message)
    
    def set_progress(self, value: int):
        """Set progress bar value (0-100)"""
        if value > 0:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(value)
        else:
            self.progress_bar.setVisible(False)
            self.progress_bar.setValue(0)
    
    def reset(self):
        """Reset status bar to initial state"""
        self.set_status("Ready")
        self.set_progress(0)
