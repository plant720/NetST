"""
Menu Bar Builder Module

Builds the application menu bar with language switching support.
"""

from typing import Callable, Optional, Dict

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenuBar, QMenu

from .language_manager import lang_manager


class MenuBarBuilder:
    """
    Menu Bar Builder Class
    
    Creates and configures the application menu bar.
    Supports rebuilding when language changes.
    """

    def __init__(self, parent):
        """Initialize the menu bar builder"""
        self.parent = parent
        self.menubar: Optional[QMenuBar] = None
        self.callbacks: Dict[str, Callable] = {}
        self.actions: Dict[str, QAction] = {}
        self.menus: Dict[str, QMenu] = {}

    def build(self, callbacks: Dict[str, Callable]) -> QMenuBar:
        """Build the complete menu bar"""
        self.callbacks = callbacks
        self.menubar = self.parent.menuBar()

        # Show menu bar inside window (not on macOS screen top)
        self.menubar.setNativeMenuBar(False)

        # QAction objects are parented to the main window rather than to their
        # menu. Merely clearing the menu bar leaves old actions and signal
        # connections alive after every language switch, so schedule the
        # previous object tree for deletion before rebuilding it.
        previous_actions = list(self.actions.values())
        previous_menus = list(dict.fromkeys(self.menus.values()))
        self.menubar.clear()
        for action in previous_actions:
            action.deleteLater()
        for menu in previous_menus:
            menu.deleteLater()
        self.actions.clear()
        self.menus.clear()

        # Build all menus
        self._build_file_menu()
        self._build_analysis_menu()
        self._build_tools_menu()
        self._build_help_menu()

        return self.menubar

    def rebuild(self):
        """Rebuild menu bar after language switch"""
        if self.callbacks:
            self.build(self.callbacks)

    def _create_action(self, text_key: str, callback_key: str) -> QAction:
        """Create a menu action item"""
        text = lang_manager.get(text_key, text_key)
        action = QAction(text, self.parent)

        if callback_key in self.callbacks:
            action.triggered.connect(self.callbacks[callback_key])

        self.actions[callback_key] = action
        return action

    def _build_file_menu(self):
        """Build the File menu"""
        file_menu = self.menubar.addMenu(lang_manager.get('menu_file'))
        self.menus['file'] = file_menu

        file_menu.addAction(self._create_action('menu_load_sequence', 'load_sequence'))
        file_menu.addAction(self._create_action('menu_load_nexus', 'load_nexus'))
        file_menu.addAction(self._create_action('menu_load_phylip', 'load_phylip'))
        file_menu.addAction(self._create_action('menu_load_vcf', 'load_vcf'))
        file_menu.addSeparator()
        file_menu.addAction(self._create_action('menu_load_csv_traits', 'load_csv_traits'))
        file_menu.addSeparator()
        file_menu.addAction(self._create_action(
            'menu_export_sequence', 'export_sequences'))
        file_menu.addAction(self._create_action(
            'menu_export_traits', 'export_traits'))
        file_menu.addSeparator()
        file_menu.addAction(self._create_action('menu_exit', 'exit'))

    def _build_analysis_menu(self):
        """Build the Analysis menu"""
        analysis_menu = self.menubar.addMenu(lang_manager.get('menu_analysis'))
        self.menus['analysis'] = analysis_menu

        analysis_menu.addAction(self._create_action('menu_build_haplotype_network', 'build_haplotype_network'))
        analysis_menu.addSeparator()

        interpretation_menu = analysis_menu.addMenu(
            lang_manager.get('menu_interpretation_analysis', 'Interpretation Analysis'))
        interpretation_menu.addAction(self._create_action(
            'menu_diversity_qc', 'analyze_diversity_qc'))
        interpretation_menu.addAction(self._create_action(
            'menu_distance_pcoa', 'analyze_distance_pcoa'))
        interpretation_menu.addAction(self._create_action(
            'menu_topology_metrics', 'analyze_topology'))
        self.menus['interpretation'] = interpretation_menu

    def _build_tools_menu(self):
        """Build the Tools menu"""
        tools_menu = self.menubar.addMenu(lang_manager.get('menu_tools'))
        self.menus['tools'] = tools_menu

        tools_menu.addAction(self._create_action('menu_msa', 'run_msa'))
        tools_menu.addAction(self._create_action(
            'menu_calculate_haplotype', 'calculate_haplotype'))
        tools_menu.addSeparator()
        tools_menu.addAction(self._create_action(
            'menu_format_conversion', 'format_conversion'))
        tools_menu.addSeparator()

        # Language submenu
        language_menu = tools_menu.addMenu(lang_manager.get('menu_language'))
        language_menu.addAction(self._create_action('menu_chinese', 'language_chinese'))
        language_menu.addAction(self._create_action('menu_english', 'language_english'))

    def _build_help_menu(self):
        """Build the Help menu"""
        help_menu = self.menubar.addMenu(lang_manager.get('menu_help'))
        self.menus['help'] = help_menu

        help_menu.addAction(self._create_action('menu_about', 'about'))
        help_menu.addSeparator()
        help_menu.addAction(self._create_action('menu_help_tcsbu', 'help_tcsbu'))
        help_menu.addAction(self._create_action('menu_help_netst', 'help_netst'))

    def get_action(self, key: str) -> Optional[QAction]:
        """Get menu action by key"""
        return self.actions.get(key)

    def set_action_enabled(self, key: str, enabled: bool):
        """Set menu action enabled state"""
        action = self.actions.get(key)
        if action:
            action.setEnabled(enabled)
