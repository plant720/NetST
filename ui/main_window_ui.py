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
    QApplication, QTextEdit, QSplitter, QPushButton
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
from .index_tab_widget import IndexTabWidget
from .haplotype_tab_widget import HaplotypeTabWidget


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
        'index': "Home",
        'network': "Network",
        'data': "Data",
        'haplotype': "Haplotype",
    }

    def __init__(self):
        """Initialize main window UI"""
        super().__init__()

        # Component references
        self.tab_widget: Optional[QTabWidget] = None
        self.index_tab: Optional[IndexTabWidget] = None
        self.web_view_main: Optional[QWebEngineView] = None
        self.data_tab: Optional[DataTabWidget] = None
        self.haplotype_tab: Optional[HaplotypeTabWidget] = None  # hidden until first analysis
        self.output_panel: Optional[OutputPanel] = None
        self._panel_toggle_btn: Optional[QPushButton] = None
        self._panel_last_width: int = 300

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
        main_layout.setSpacing(0)

        # Splitter for resizable left/right panels
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side: Tab widget
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.tab_widget = QTabWidget()
        left_layout.addWidget(self.tab_widget)

        # Create tabs (order: Home, Data, Network)
        # Haplotype tab is NOT added here — it appears only after a successful analysis.
        self._create_index_tab()
        self._create_data_tab()
        self._create_network_tab()

        self._splitter.addWidget(left_widget)

        # Right side: Output panel
        self.output_panel = OutputPanel()
        self.output_panel.setMinimumWidth(180)
        self.output_panel.setMaximumWidth(500)
        self._splitter.addWidget(self.output_panel)

        # Right panel cannot be fully collapsed via splitter handle
        self._splitter.setCollapsible(0, False)
        self._splitter.setCollapsible(1, False)
        self._splitter.setSizes([1100, 300])

        main_layout.addWidget(self._splitter, 1)

        # Narrow toggle strip to the right of the splitter (always visible)
        self._panel_toggle_btn = QPushButton("▶")
        self._panel_toggle_btn.setFixedWidth(18)
        self._panel_toggle_btn.setToolTip("Collapse output panel")
        self._panel_toggle_btn.setStyleSheet(
            "QPushButton {"
            "  border: none;"
            "  background: #e0e0e0;"
            "  color: #555;"
            "  font-size: 10px;"
            "}"
            "QPushButton:hover { background: #c8c8c8; }"
        )
        self._panel_toggle_btn.clicked.connect(self._toggle_output_panel)
        main_layout.addWidget(self._panel_toggle_btn)

        # Create status bar
        self.status_bar_widget = StatusBarWidget(self)

    def _toggle_output_panel(self):
        """Show or hide the entire output panel via the splitter."""
        if self.output_panel.isVisible():
            self._panel_last_width = self._splitter.sizes()[1]
            self.output_panel.setVisible(False)
            self._panel_toggle_btn.setText("◀")
            self._panel_toggle_btn.setToolTip("Expand output panel")
        else:
            self.output_panel.setVisible(True)
            total = sum(self._splitter.sizes())
            restore = self._panel_last_width or 300
            self._splitter.setSizes([total - restore, restore])
            self._panel_toggle_btn.setText("▶")
            self._panel_toggle_btn.setToolTip("Collapse output panel")

    def _create_index_tab(self):
        """Create the Index (welcome) tab — always the first tab."""
        self.index_tab = IndexTabWidget()
        self.tab_widget.addTab(self.index_tab, self.TAB_NAMES['index'])

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

    def setup_menus(self, callbacks: Dict[str, Callable]):
        """Setup menu bar"""
        self.menu_builder = MenuBarBuilder(self)
        self.menu_builder.build(callbacks)

    def load_main_page(self, html_path: str):
        """Load main network view page"""
        if os.path.isfile(html_path):
            self.web_view_main.setUrl(QUrl.fromLocalFile(html_path))

    def switch_to_tab(self, tab_name: str):
        """Switch to the named tab using widget references (robust against index changes)."""
        widget_map = {
            'index': self.index_tab,
            'network': self.web_view_main,
            'data': self.data_tab,
            'haplotype': self.haplotype_tab,
        }
        widget = widget_map.get(tab_name)
        if widget is not None:
            idx = self.tab_widget.indexOf(widget)
            if idx >= 0:
                self.tab_widget.setCurrentIndex(idx)

    def show_haplotype_tab(self, output_path: str, prefix: str) -> None:
        """Create (once) and show the Haplotype tab, then load the latest results.

        Safe to call repeatedly — avoids adding duplicate tabs on re-analysis.
        """
        if self.haplotype_tab is None:
            # First successful analysis: create and register the tab
            self.haplotype_tab = HaplotypeTabWidget()
            self.tab_widget.addTab(self.haplotype_tab, self.TAB_NAMES['haplotype'])

        # Always refresh content so re-runs show up-to-date data
        self.haplotype_tab.load_result(output_path, prefix)

        # Switch focus to the haplotype tab so the user notices it
        self.switch_to_tab('haplotype')

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

    def get_project_prefix(self) -> str:
        """Get project name used as output file prefix."""
        if self.output_panel:
            return self.output_panel.get_project_prefix()
        return "project"

    # Compatibility property for log_tab
    @property
    def log_tab(self):
        """Compatibility property - returns output_panel"""
        return self.output_panel
