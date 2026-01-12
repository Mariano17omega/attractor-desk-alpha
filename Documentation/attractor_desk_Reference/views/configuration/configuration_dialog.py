"""Configuration dialog with sidebar navigation."""

from typing import Optional, TYPE_CHECKING

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QScrollArea,
    QFrame,
)

from ...viewmodels import SettingsViewModel
from .theme_page import ThemePage
from .models_page import ModelsPage
from .shortcuts_page import ShortcutsPage
from .rag_page import RagPage
from .deep_research_page import DeepResearchPage
from .memory_page import MemoryPage

if TYPE_CHECKING:
    from ...infrastructure import RagService


class ConfigurationDialog(QDialog):
    """Modal configuration dialog with sidebar navigation."""
    
    settings_saved = Signal()
    transparency_preview = Signal(int)
    
    # Category names, indices, and icon filenames
    CATEGORIES = [
        ("Models", 0, "model_settings.svg"),
        ("Deep Research", 1, "deep_research_settings.svg"),
        ("RAG", 2, "rag_settings.svg"),
        ("Memory", 3, "agent_settings.svg"),
        ("Shortcuts", 4, "shortcuts_settings.svg"),
        ("Theme", 5, "thema_settings.svg"),
    ]
    
    def __init__(
        self,
        viewmodel: SettingsViewModel,
        rag_service: Optional["RagService"] = None,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the configuration dialog.
        
        Args:
            viewmodel: The settings viewmodel.
            rag_service: The RAG service for indexing operations.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._viewmodel = viewmodel
        self._rag_service = rag_service
        self._original_transparency = viewmodel.transparency
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        self.setWindowTitle("Settings")
        self.setMinimumSize(1100, 800) # Increased slightly to ensure comfortable fit
        self.setModal(True)
        
        # Apply dialog-specific styles
        self.setStyleSheet(self._get_dialog_styles())
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Content area (sidebar + stacked widget)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(0)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Sidebar
        self._sidebar = QListWidget()
        self._sidebar.setObjectName("configSidebar")
        self._sidebar.setFixedWidth(200) # Slightly wider for icons
        self._sidebar.setIconSize(QSize(20, 20))
        self._sidebar.setSpacing(4) # Slight spacing between items
        
        # Resolve assets path (assets is inside attractor_desk package)
        from pathlib import Path
        self._assets_dir = Path(__file__).resolve().parents[2] / "assets" / "icons"
        
        for name, _, icon_file in self.CATEGORIES:
            item = QListWidgetItem(name)

            # Adjust size hint for better touch target/visual
            item.setSizeHint(QSize(0, 44)) # Fixed height per item
            
            self._sidebar.addItem(item)
            
        self._sidebar.setCurrentRow(0)
        self._apply_sidebar_icons()
        
        content_layout.addWidget(self._sidebar)
        
        # Stacked widget for pages
        self._stack = QStackedWidget()
        self._stack.setObjectName("configContent")
        
        # Create pages
        self._models_page = ModelsPage(self._viewmodel)
        self._deep_research_page = DeepResearchPage()
        self._rag_page = RagPage(
            settings_viewmodel=self._viewmodel,
            rag_service=self._rag_service,
        )
        self._memory_page = MemoryPage(self._viewmodel)
        self._shortcuts_page = ShortcutsPage(self._viewmodel)
        self._theme_page = ThemePage(self._viewmodel)
        
        # Add pages in order matching CATEGORIES
        self._stack.addWidget(self._wrap_in_scroll_area(self._models_page))      # 0
        self._stack.addWidget(self._wrap_in_scroll_area(self._deep_research_page))  # 1
        self._stack.addWidget(self._wrap_in_scroll_area(self._rag_page))         # 2
        self._stack.addWidget(self._wrap_in_scroll_area(self._memory_page))      # 3
        self._stack.addWidget(self._wrap_in_scroll_area(self._shortcuts_page))   # 4
        self._stack.addWidget(self._wrap_in_scroll_area(self._theme_page))       # 5
        
        content_layout.addWidget(self._stack)
        
        # Add content to main layout
        content_widget = QWidget()
        content_widget.setLayout(content_layout)
        main_layout.addWidget(content_widget, 1)
        
        # Bottom button bar
        button_bar = QWidget()
        button_bar.setObjectName("buttonBar")
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(20, 15, 20, 15)
        
        button_layout.addStretch()
        
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("cancelButton")
        self._cancel_btn.setMinimumWidth(120)
        
        self._save_btn = QPushButton("Save Configuration")
        self._save_btn.setObjectName("saveButton")
        self._save_btn.setMinimumWidth(150)
        
        button_layout.addWidget(self._cancel_btn)
        button_layout.addWidget(self._save_btn)
        
        main_layout.addWidget(button_bar)
    
    def _connect_signals(self) -> None:
        """Connect signals."""
        self._sidebar.currentRowChanged.connect(self._on_category_changed)
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._save_btn.clicked.connect(self._on_save)
        self._theme_page.transparency_preview_requested.connect(
            self.transparency_preview.emit
        )
        self._viewmodel.settings_changed.connect(self._update_styles)

    def _update_styles(self) -> None:
        """Update styles when settings change."""
        self.setStyleSheet(self._get_dialog_styles())
        self._apply_sidebar_icons()
    
    def _on_category_changed(self, row: int) -> None:
        """Handle category selection change."""
        self._stack.setCurrentIndex(row)
    
    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        # Restore original transparency
        self.transparency_preview.emit(self._original_transparency)
        self.reject()
    
    def _on_save(self) -> None:
        """Handle save button click."""
        self._viewmodel.save_settings()
        self.settings_saved.emit()
        self.accept()
    
    def _get_dialog_styles(self) -> str:
        """Get dialog-specific styles."""
        # Dynamically import COLORS to avoid circular import issues at toplevel if any
        from ..styles import (
            COLORS,
            get_dark_theme_stylesheet,
            get_light_theme_stylesheet,
        )
        from ...core.models import ThemeMode
        
        mode = self._viewmodel.theme_mode
        c = COLORS["dark"] if mode == ThemeMode.DARK else COLORS["light"]
        p = COLORS
        
        base_styles = (
            get_dark_theme_stylesheet()
            if mode == ThemeMode.DARK
            else get_light_theme_stylesheet()
        )
        dialog_styles = f"""
        QDialog {{
            background-color: {c['background']};
        }}
        
        QListWidget#configSidebar {{
            background-color: {c['surface']};
            border: none;
            border-right: 1px solid {c['border']};
            padding: 10px 0;
            outline: none;
        }}
        
        QListWidget#configSidebar::item {{
            color: {c['text_secondary']};
            padding: 12px 20px;
            border-radius: 8px;
            margin: 4px 8px;
            border: 1px solid transparent;
            font-weight: 500;
        }}
        
        QListWidget#configSidebar::item:selected {{
            background-color: {p['primary_fade']};
            color: {c['text_primary']};
            border: 1px solid {p['primary_hover']};
        }}
        
        QListWidget#configSidebar::item:hover:!selected {{
            background-color: {c['surface_highlight']};
            color: {c['text_primary']};
        }}
        
        QStackedWidget#configContent {{
            background-color: {c['background']};
        }}
        
        QWidget#buttonBar {{
            background-color: {c['surface']};
            border-top: 1px solid {c['border']};
        }}
        
        QPushButton#cancelButton {{
            background-color: transparent;
            color: {c['text_muted']};
            border: 1px solid {c['border']};
            border-radius: 8px;
            padding: 8px 16px;
        }}
        
        QPushButton#cancelButton:hover {{
            background-color: {c['surface_highlight']};
            color: {c['text_primary']};
        }}
        
        QPushButton#saveButton {{
            background-color: {p['primary']};
            color: #FFFFFF;
            border: none;
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: bold;
        }}
        
        QPushButton#saveButton:hover {{
            background-color: {p['primary_dark']};
        }}
        """
        return f"{base_styles}\n{dialog_styles}"

    def _apply_sidebar_icons(self) -> None:
        """Apply theme-aware icons in the sidebar."""
        from ..styles import COLORS
        from ...core.models import ThemeMode

        mode = self._viewmodel.theme_mode
        c = COLORS["dark"] if mode == ThemeMode.DARK else COLORS["light"]
        icon_color = c["text_primary"]

        icon_size = self._sidebar.iconSize()
        for index, (_, _, icon_file) in enumerate(self.CATEGORIES):
            item = self._sidebar.item(index)
            if item is None:
                continue
            icon_path = self._assets_dir / icon_file
            if not icon_path.exists():
                item.setIcon(QIcon())
                continue
            base_icon = QIcon(str(icon_path))
            if mode == ThemeMode.DARK:
                item.setIcon(self._tint_icon(base_icon, icon_color, icon_size))
            else:
                item.setIcon(base_icon)

    @staticmethod
    def _tint_icon(icon: QIcon, color: str, size: QSize) -> QIcon:
        """Tint an icon to the requested color while preserving alpha."""
        pixmap = icon.pixmap(size)
        if pixmap.isNull():
            return icon
        tinted = QPixmap(pixmap.size())
        tinted.setDevicePixelRatio(pixmap.devicePixelRatio())
        tinted.fill(Qt.transparent)
        painter = QPainter(tinted)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), QColor(color))
        painter.end()
        return QIcon(tinted)

    def _wrap_in_scroll_area(self, widget: QWidget) -> QScrollArea:
        """Wrap a widget in a scroll area.
        
        Args:
            widget: The widget to wrap.
            
        Returns:
            The scroll area containing the widget.
        """
        scroll = QScrollArea()
        scroll.setWidget(widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        # Only vertical scrolling
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        return scroll
