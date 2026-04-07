"""
Output Panel Module

Right side panel containing output folder selection and log display.
"""

import os
import subprocess
import sys
from datetime import datetime
from typing import Optional

from PyQt6.QtGui import QColor, QTextCursor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QLineEdit, QFrame, QFileDialog, QSizePolicy
)


class OutputPanel(QWidget):
    """
    Output Panel Widget
    
    Contains output folder selection and log display area.
    Fixed on the right side of the main window.
    """

    LOG_COLORS = {
        'INFO': QColor('#333333'),
        'SUCCESS': QColor('#4CAF50'),
        'WARNING': QColor('#FF9800'),
        'ERROR': QColor('#F44336'),
        'DEBUG': QColor('#9E9E9E')
    }

    def __init__(self, parent: QWidget = None):
        """Initialize the output panel"""
        super().__init__(parent)

        self.project_name_edit: Optional[QLineEdit] = None
        self.output_path_edit: Optional[QLineEdit] = None
        self.log_text: Optional[QTextEdit] = None
        self.btn_open: Optional[QPushButton] = None
        self.btn_change: Optional[QPushButton] = None
        self.hint_label: Optional[QLabel] = None
        self.btn_toggle_log: Optional[QPushButton] = None
        self.log_frame: Optional[QFrame] = None

        # Default output path
        self.output_path = os.path.join(os.path.expanduser("~"), "HaplotypeOutput")

        self._setup_ui()

    def _setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Output folder section
        output_frame = self._create_output_section()
        layout.addWidget(output_frame)

        # Log section
        self.log_frame = self._create_log_section()
        layout.addWidget(self.log_frame, 1)  # Stretch factor 1

    def _create_output_section(self) -> QFrame:
        """Create output folder section"""
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setFrameShadow(QFrame.Shadow.Raised)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)

        # Title
        title_label = QLabel("Output")
        title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(title_label)

        # Project name (file prefix)
        layout.addWidget(QLabel("Project Name:"))
        self.project_name_edit = QLineEdit()
        self.project_name_edit.setPlaceholderText("e.g. my_project")
        self.project_name_edit.setText("project")
        layout.addWidget(self.project_name_edit)

        # Output folder path
        layout.addWidget(QLabel("Output Folder:"))
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setText(self.output_path)
        self.output_path_edit.setReadOnly(True)
        layout.addWidget(self.output_path_edit)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)

        self.btn_open = QPushButton("Open")
        self.btn_open.clicked.connect(self._open_output_folder)
        btn_layout.addWidget(self.btn_open)

        self.btn_change = QPushButton("Change")
        self.btn_change.clicked.connect(self._change_output_folder)
        btn_layout.addWidget(self.btn_change)

        layout.addLayout(btn_layout)

        return frame

    def _create_log_section(self) -> QFrame:
        """Create log display section"""
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setFrameShadow(QFrame.Shadow.Raised)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)

        # Header row: label + toggle button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.hint_label = QLabel("Logs")
        self.hint_label.setStyleSheet("color: #666666;")
        header_layout.addWidget(self.hint_label)

        header_layout.addStretch()

        self.btn_toggle_log = QPushButton("▼")
        self.btn_toggle_log.setFixedSize(20, 20)
        self.btn_toggle_log.setToolTip("Collapse log")
        self.btn_toggle_log.setStyleSheet(
            "QPushButton { border: none; color: #666666; font-size: 10px; }"
            "QPushButton:hover { color: #333333; }"
        )
        self.btn_toggle_log.clicked.connect(self._toggle_log)
        header_layout.addWidget(self.btn_toggle_log)

        layout.addLayout(header_layout)

        # Log text
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier New", 9))
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.log_text)

        return frame

    def _toggle_log(self):
        """Toggle log text area visibility."""
        visible = self.log_text.isVisible()
        self.log_text.setVisible(not visible)
        if visible:
            self.btn_toggle_log.setText("▶")
            self.btn_toggle_log.setToolTip("Expand log")
            self.log_frame.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum
            )
        else:
            self.btn_toggle_log.setText("▼")
            self.btn_toggle_log.setToolTip("Collapse log")
            self.log_frame.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
            )

    def _open_output_folder(self):
        """Open output folder in file explorer"""
        path = self.output_path_edit.text()

        # Create folder if not exists
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except Exception:
                pass

        # Open in file explorer
        if os.path.exists(path):
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', path])
            else:
                subprocess.run(['xdg-open', path])

    def _change_output_folder(self):
        """Change output folder"""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Output Folder", self.output_path
        )

        if folder:
            self.output_path = folder
            self.output_path_edit.setText(folder)

    def get_project_prefix(self) -> str:
        """Get the project name used as output file prefix."""
        return self.project_name_edit.text().strip()

    def set_project_prefix(self, name: str):
        """Set the project name / file prefix."""
        self.project_name_edit.setText(name)

    def get_output_path(self) -> str:
        """Get current output path"""
        return self.output_path_edit.text()

    def set_output_path(self, path: str):
        """Set output path"""
        self.output_path = path
        self.output_path_edit.setText(path)

    def append_log(self, message: str, level: str = 'INFO'):
        """Append log message with specified level"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] {message}"

        color = self.LOG_COLORS.get(level, self.LOG_COLORS['INFO'])

        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)

        self.log_text.setTextColor(color)
        self.log_text.append(log_line)

        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def append_info(self, message: str):
        """Append info level log"""
        self.append_log(message, 'INFO')

    def append_success(self, message: str):
        """Append success level log"""
        self.append_log(message, 'SUCCESS')

    def append_warning(self, message: str):
        """Append warning level log"""
        self.append_log(message, 'WARNING')

    def append_error(self, message: str):
        """Append error level log"""
        self.append_log(message, 'ERROR')

    def clear_log(self):
        """Clear log content"""
        self.log_text.clear()

    def get_log_content(self) -> str:
        """Get log content"""
        return self.log_text.toPlainText()

    def update_language(self):
        """Update interface language"""
        from .language_manager import lang_manager
        self.btn_open.setText(lang_manager.get('btn_open'))
        self.btn_change.setText(lang_manager.get('btn_change'))
        self.hint_label.setText(lang_manager.get('log_hint'))
