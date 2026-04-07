"""
Menu Bar Builder Module

Builds the application menu bar with language switching support.
"""

from typing import Callable, Optional, Dict
from PyQt6.QtWidgets import QMenuBar, QMenu
from PyQt6.QtGui import QAction

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
        
        # Clear existing menus
        self.menubar.clear()
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
        file_menu.addAction(self._create_action('menu_add_sequence', 'add_sequence'))
        file_menu.addSeparator()
        file_menu.addAction(self._create_action('menu_export_sequence', 'export_fasta'))
        file_menu.addSeparator()
        file_menu.addAction(self._create_action('menu_exit', 'exit'))
    
    def _build_analysis_menu(self):
        """Build the Analysis menu"""
        analysis_menu = self.menubar.addMenu(lang_manager.get('menu_analysis'))
        self.menus['analysis'] = analysis_menu
        
        # Haplotype Network
        analysis_menu.addAction(self._create_action('menu_msn_network', 'network_msn'))
        analysis_menu.addAction(self._create_action('menu_mjn_network', 'network_mjn'))
        analysis_menu.addAction(self._create_action('menu_tcs_network', 'network_tcs'))
        analysis_menu.addSeparator()
        
        # MAFFT submenu
        mafft_menu = analysis_menu.addMenu(lang_manager.get('menu_mafft'))
        mafft_menu.addAction(self._create_action('menu_mafft_auto', 'mafft_auto'))
        mafft_menu.addAction(self._create_action('menu_mafft_fftns1', 'mafft_fftns1'))
        mafft_menu.addAction(self._create_action('menu_mafft_fftns2', 'mafft_fftns2'))
        mafft_menu.addAction(self._create_action('menu_mafft_ginsi', 'mafft_ginsi'))
        mafft_menu.addAction(self._create_action('menu_mafft_linsi', 'mafft_linsi'))
        mafft_menu.addAction(self._create_action('menu_mafft_einsi', 'mafft_einsi'))
        
        # MUSCLE submenu
        muscle_menu = analysis_menu.addMenu(lang_manager.get('menu_muscle'))
        muscle_menu.addAction(self._create_action('menu_muscle_ppp', 'muscle_ppp'))
        muscle_menu.addAction(self._create_action('menu_muscle_super5', 'muscle_super5'))
        
        analysis_menu.addSeparator()
        
        # Network Analysis
        analysis_menu.addAction(self._create_action('menu_network_visualization', 'network_visualization'))
        analysis_menu.addAction(self._create_action('menu_topology_analysis', 'topology_analysis'))
        
        # Community Detection submenu
        community_menu = analysis_menu.addMenu(lang_manager.get('menu_community_detection'))
        community_menu.addAction(self._create_action('menu_modularity_analysis', 'modularity_analysis'))
        community_menu.addAction(self._create_action('menu_community_plot', 'community_plot'))
        
        analysis_menu.addSeparator()
        
        # Statistical Analysis
        analysis_menu.addAction(self._create_action('menu_sequence_analysis', 'sequence_analysis'))
        analysis_menu.addAction(self._create_action('menu_population_analysis', 'population_analysis'))
        analysis_menu.addAction(self._create_action('menu_trait_analysis', 'trait_analysis'))
    
    def _build_tools_menu(self):
        """Build the Tools menu"""
        tools_menu = self.menubar.addMenu(lang_manager.get('menu_tools'))
        self.menus['tools'] = tools_menu
        
        # Language submenu
        language_menu = tools_menu.addMenu(lang_manager.get('menu_language'))
        language_menu.addAction(self._create_action('menu_chinese', 'language_chinese'))
        language_menu.addAction(self._create_action('menu_english', 'language_english'))
    
    def _build_help_menu(self):
        """Build the Help menu"""
        help_menu = self.menubar.addMenu(lang_manager.get('menu_help'))
        self.menus['help'] = help_menu
        
        help_menu.addAction(self._create_action('menu_about', 'about'))
        help_menu.addAction(self._create_action('menu_help_docs', 'help_docs'))
    
    def get_action(self, key: str) -> Optional[QAction]:
        """Get menu action by key"""
        return self.actions.get(key)
    
    def set_action_enabled(self, key: str, enabled: bool):
        """Set menu action enabled state"""
        action = self.actions.get(key)
        if action:
            action.setEnabled(enabled)
