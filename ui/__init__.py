"""
UI Module - User Interface Components Package

Contains all PyQt6 UI component classes, separating UI design from business logic.
"""

from .alignment_tab_widget import AlignmentTabWidget
from .data_tab_widget import DataTabWidget
from .haplotype_tab_widget import HaplotypeTabWidget
from .index_tab_widget import IndexTabWidget
from .language_manager import LanguageManager, lang_manager
from .main_window_ui import MainWindowUI
from .menu_bar import MenuBarBuilder
from .output_panel import OutputPanel
from .sequence_alignment_dialog import SequenceAlignmentDialog, SequenceAlignmentConfig
from .standardization_dialog import StandardizationDialog, StandardizationConfig
from .status_bar import StatusBarWidget

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
    'AlignmentTabWidget',
]
