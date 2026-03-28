"""
Main Window UI Module

Defines the main window UI layout and component initialization,
separating UI design from business logic.
"""

import os
from typing import Optional, Dict, Callable

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
    QApplication, QTextEdit, QSplitter
)

# Safe WebEngine import with fallback
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False
    print("Warning: PyQt6-WebEngine not available. Using fallback text widget.")
    QWebEngineView = None

from .menu_bar import MenuBarBuilder
from .status_bar import StatusBarWidget
from .data_tab_widget import DataTabWidget
from .output_panel import OutputPanel


class FallbackWebView(QTextEdit):
    """Fallback widget when WebEngine is not available"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setText("WebEngine not available\n\n"
                     "Please install PyQt6-WebEngine:\npip install PyQt6-WebEngine")
    
    def setUrl(self, url):
        self.setText(f"URL: {url.toString() if hasattr(url, 'toString') else url}")
    
    def back(self):
        pass
    
    def forward(self):
        pass


class MainWindowUI(QMainWindow):
    """
    Main Window UI Base Class
    
    Layout:
    +--------------------------------------------------+
    | Menu Bar                                          |
    +----------------------------------+---------------+
    |                                  |    Output     |
    |     Tab Widget                   |   [path]      |
    |  (Network, Data, Report)         |  [Open][Change]|
    |                                  |               |
    |                                  |    Log        |
    |                                  |   [messages]  |
    |                                  |               |
    +----------------------------------+---------------+
    | Status Bar                                        |
    +--------------------------------------------------+
    """
    
    DEFAULT_WINDOW_TITLE = "Haplotype Network Analysis Tool"
    DEFAULT_WINDOW_SIZE = (1400, 900)
    DEFAULT_WINDOW_POSITION = (100, 100)
    
    TAB_NAMES = {
        'network': "Network View",
        'data': "Data",
        'report': "Analysis Report"
    }
    
    def __init__(self):
        """Initialize main window UI"""
        super().__init__()
        
        # Component references
        self.tab_widget: Optional[QTabWidget] = None
        self.web_view_main: Optional[QWebEngineView] = None
        self.web_view_analysis: Optional[QWebEngineView] = None
        self.data_tab: Optional[DataTabWidget] = None
        self.output_panel: Optional[OutputPanel] = None
        
        # UI builders
        self.menu_builder: Optional[MenuBarBuilder] = None
        self.status_bar_widget: Optional[StatusBarWidget] = None
        
        # Application directory
        self.current_directory = os.path.dirname(os.path.abspath(__file__))
        self.current_directory = os.path.dirname(self.current_directory)
        
        # Language setting
        self.language = "en"
        
        # Initialize UI
        self._init_window()
        self._init_ui()
    
    def _init_window(self):
        """Initialize window basic properties"""
        self.setWindowTitle(self.DEFAULT_WINDOW_TITLE)
        x, y = self.DEFAULT_WINDOW_POSITION
        width, height = self.DEFAULT_WINDOW_SIZE
        self.setGeometry(x, y, width, height)
    
    def _center_on_screen(self):
        """Center the window on screen"""
        screen = QApplication.primaryScreen().geometry()
        window_geometry = self.geometry()
        x = (screen.width() - window_geometry.width()) // 2
        y = (screen.height() - window_geometry.height()) // 2
        self.move(x, y)
    
    def _init_ui(self):
        """Initialize user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left side: Tab widget
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tab_widget = QTabWidget()
        left_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self._create_network_tab()
        self._create_data_tab()
        self._create_report_tab()
        
        splitter.addWidget(left_widget)
        
        # Right side: Output panel
        self.output_panel = OutputPanel()
        self.output_panel.setMinimumWidth(200)
        self.output_panel.setMaximumWidth(350)
        splitter.addWidget(self.output_panel)
        
        # Set splitter sizes (left: 80%, right: 20%)
        splitter.setSizes([1100, 300])
        
        # Create status bar
        self.status_bar_widget = StatusBarWidget(self)
    
    def _create_network_tab(self):
        """Create network view tab"""
        if WEBENGINE_AVAILABLE:
            self.web_view_main = QWebEngineView()
            self.web_view_main.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        else:
            self.web_view_main = FallbackWebView()
        
        self.tab_widget.addTab(self.web_view_main, self.TAB_NAMES['network'])
    
    def _create_data_tab(self):
        """Create data tab"""
        self.data_tab = DataTabWidget()
        self.tab_widget.addTab(self.data_tab, self.TAB_NAMES['data'])
    
    def _create_report_tab(self):
        """Create analysis report tab"""
        if WEBENGINE_AVAILABLE:
            self.web_view_analysis = QWebEngineView()
            self.web_view_analysis.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        else:
            self.web_view_analysis = FallbackWebView()
        
        self.tab_widget.addTab(self.web_view_analysis, self.TAB_NAMES['report'])
    
    def setup_menus(self, callbacks: Dict[str, Callable]):
        """Setup menu bar"""
        self.menu_builder = MenuBarBuilder(self)
        self.menu_builder.build(callbacks)
    
    def load_main_page(self, html_path: str):
        """Load main network view page"""
        if os.path.isfile(html_path):
            self.web_view_main.setUrl(QUrl.fromLocalFile(html_path))
    
    def load_report_page(self, html_path: str):
        """Load analysis report page"""
        if os.path.isfile(html_path):
            self.web_view_analysis.setUrl(QUrl.fromLocalFile(html_path))
    
    def switch_to_tab(self, tab_name: str):
        """Switch to specified tab"""
        tab_indices = {'network': 0, 'data': 1, 'report': 2}
        if tab_name in tab_indices:
            self.tab_widget.setCurrentIndex(tab_indices[tab_name])
    
    def set_status(self, message: str):
        """Set status bar message"""
        if self.status_bar_widget:
            self.status_bar_widget.set_status(message)
    
    def set_progress(self, value: int):
        """Set progress bar value (0-100)"""
        if self.status_bar_widget:
            self.status_bar_widget.set_progress(value)
    
    def append_log(self, message: str, level: str = 'INFO'):
        """Append log message"""
        if self.output_panel:
            self.output_panel.append_log(message, level)
    
    def get_current_directory(self) -> str:
        """Get application directory"""
        return self.current_directory
    
    def get_output_path(self) -> str:
        """Get output path"""
        if self.output_panel:
            return self.output_panel.get_output_path()
        return ""
    
    # Compatibility property for log_tab
    @property
    def log_tab(self):
        """Compatibility property - returns output_panel"""
        return self.output_panel
