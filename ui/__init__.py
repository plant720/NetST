"""
UI Module - User Interface Components Package

Contains all PyQt6 UI component classes, separating UI design from business logic.
"""

from .main_window_ui import MainWindowUI
from .menu_bar import MenuBarBuilder
from .status_bar import StatusBarWidget
from .data_tab_widget import DataTabWidget
from .output_panel import OutputPanel
from .language_manager import LanguageManager, lang_manager
from .standardization_dialog import StandardizationDialog, StandardizationConfig
from .sequence_alignment_dialog import SequenceAlignmentDialog, SequenceAlignmentConfig
from .index_tab_widget import IndexTabWidget
from .haplotype_tab_widget import HaplotypeTabWidget

__all__ = [
    'MainWindowUI',
    'MenuBarBuilder',
    'StatusBarWidget',
    'DataTabWidget',
    'OutputPanel',
    'LanguageManager',
    'lang_manager',
    'StandardizationDialog',
    'StandardizationConfig',
    'SequenceAlignmentDialog',
    'SequenceAlignmentConfig',
    'IndexTabWidget',
    'HaplotypeTabWidget',
]
