"""
Output Panel Module

Right side panel containing output folder selection and log display.
"""

import os
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QColor, QTextCursor, QFont, QDesktopServices
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QLineEdit, QFrame, QFileDialog
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
        self.output_title_label: Optional[QLabel] = None
        self.project_name_label: Optional[QLabel] = None
        self.output_folder_label: Optional[QLabel] = None

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
        log_frame = self._create_log_section()
        layout.addWidget(log_frame, 1)  # Stretch factor 1

    def _create_output_section(self) -> QFrame:
        """Create output folder section"""
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setFrameShadow(QFrame.Shadow.Raised)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)

        from .language_manager import lang_manager

        # Title
        self.output_title_label = QLabel(lang_manager.get('label_output', 'Output'))
        self.output_title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(self.output_title_label)

        # Project name (file prefix)
        self.project_name_label = QLabel(lang_manager.get('label_project_name', 'Project Name:'))
        layout.addWidget(self.project_name_label)
        self.project_name_edit = QLineEdit()
        self.project_name_edit.setPlaceholderText(
            lang_manager.get('placeholder_project', 'e.g. my_project'))
        self.project_name_edit.setText("project")
        layout.addWidget(self.project_name_edit)

        # Output folder path
        self.output_folder_label = QLabel(lang_manager.get('label_output_folder', 'Output Folder:'))
        layout.addWidget(self.output_folder_label)
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setText(self.output_path)
        self.output_path_edit.setReadOnly(True)
        layout.addWidget(self.output_path_edit)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)

        self.btn_open = QPushButton(lang_manager.get('btn_open', 'Open'))
        self.btn_open.clicked.connect(self._open_output_folder)
        btn_layout.addWidget(self.btn_open)

        self.btn_change = QPushButton(lang_manager.get('btn_change', 'Change'))
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

        from .language_manager import lang_manager

        # Hint label
        self.hint_label = QLabel(lang_manager.get('log_hint', 'Logs'))
        self.hint_label.setStyleSheet("color: #666666;")
        layout.addWidget(self.hint_label)

        # Log text
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier New", 10))
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.log_text)

        return frame

    def _open_output_folder(self):
        """Open output folder in file explorer"""
        from .language_manager import lang_manager

        path = self.output_path_edit.text().strip()
        try:
            if not path:
                raise OSError('Output folder is empty')
            os.makedirs(path, exist_ok=True)
            opened = QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            if not opened:
                raise OSError(f'No desktop application could open {path}')
        except OSError as exc:
            self.append_error(lang_manager.get(
                'msg_open_output_failed',
                'Could not open the output folder: {error}').format(error=exc))

    def _change_output_folder(self):
        """Change output folder"""
        from .language_manager import lang_manager
        folder = QFileDialog.getExistingDirectory(
            self, lang_manager.get('dlg_select_output', 'Select Output Folder'),
            self.output_path
        )

        if folder:
            self.output_path = folder
            self.output_path_edit.setText(folder)

    def get_project_prefix(self) -> str:
        """Get the project name used as output file prefix."""
        return self.project_name_edit.text().strip()

    def get_output_path(self) -> str:
        """Get current output path"""
        return self.output_path_edit.text()

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

    def update_language(self):
        """Update interface language"""
        from .language_manager import lang_manager
        self.btn_open.setText(lang_manager.get('btn_open'))
        self.btn_change.setText(lang_manager.get('btn_change'))
        self.hint_label.setText(lang_manager.get('log_hint'))
        if self.output_title_label:
            self.output_title_label.setText(lang_manager.get('label_output'))
        if self.project_name_label:
            self.project_name_label.setText(lang_manager.get('label_project_name'))
        if self.output_folder_label:
            self.output_folder_label.setText(lang_manager.get('label_output_folder'))
        if self.project_name_edit:
            self.project_name_edit.setPlaceholderText(
                lang_manager.get('placeholder_project'))
