"""Configuration dialog with sidebar navigation."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

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
)

from core.models import ThemeMode
from ui.viewmodels.settings_viewmodel import SettingsViewModel
from ui.widgets.configuration.deep_search_page import DeepSearchPage
from ui.widgets.configuration.models_page import ModelsPage
from ui.widgets.configuration.placeholder_page import PlaceholderPage
from ui.widgets.configuration.rag_page import RagPage
from ui.widgets.configuration.shortcuts_page import ShortcutsPage
from ui.widgets.configuration.theme_page import ThemePage
from ui.styles import COLORS, get_dark_theme_stylesheet, get_light_theme_stylesheet


class ConfigurationDialog(QDialog):
    """Modal configuration dialog with sidebar navigation."""

    settings_saved = Signal()
    transparency_preview = Signal(int)

    CATEGORIES = [
        ("Models", 0, "model_settings.svg"),
        ("Deep Search", 1, "deep_research_settings.svg"),
        ("Deep Research", 2, "deep_research_settings.svg"),
        ("RAG", 3, "rag_settings.svg"),
        ("Memory", 4, "agent_settings.svg"),
        ("Shortcuts", 5, "shortcuts_settings.svg"),
        ("Theme", 6, "thema_settings.svg"),
    ]

    def __init__(
        self,
        viewmodel: SettingsViewModel,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._viewmodel = viewmodel
        self._initial_snapshot = viewmodel.snapshot()
        self._assets_dir = Path(__file__).resolve().parents[2] / "assets" / "icons"
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Settings")
        self.setMinimumSize(1100, 800)
        self.setModal(True)
        self.setStyleSheet(self._get_dialog_styles())

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(0)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self._sidebar = QListWidget()
        self._sidebar.setObjectName("configSidebar")
        self._sidebar.setFixedWidth(200)
        self._sidebar.setIconSize(QSize(20, 20))
        self._sidebar.setSpacing(4)

        for name, _, _ in self.CATEGORIES:
            item = QListWidgetItem(name)
            item.setSizeHint(QSize(0, 44))
            self._sidebar.addItem(item)

        self._sidebar.setCurrentRow(0)
        self._apply_sidebar_icons()
        content_layout.addWidget(self._sidebar)

        self._stack = QStackedWidget()
        self._stack.setObjectName("configContent")

        self._models_page = ModelsPage(self._viewmodel)
        self._deep_search_page = DeepSearchPage(self._viewmodel)
        self._deep_research_page = PlaceholderPage(
            "Deep Research Settings",
            "Deep Research configuration coming soon.",
            [
                "Research model selection",
                "Search depth and iterations",
                "Source preferences",
                "Output format",
            ],
        )
        self._rag_page = RagPage(self._viewmodel)
        self._memory_page = PlaceholderPage(
            "Memory Settings",
            "Memory configuration coming soon.",
            [
                "Workspace memory limits",
                "Auto-summarization",
                "Retention behavior",
            ],
        )
        self._shortcuts_page = ShortcutsPage(self._viewmodel)
        self._theme_page = ThemePage(self._viewmodel)

        self._stack.addWidget(self._wrap_in_scroll_area(self._models_page))
        self._stack.addWidget(self._wrap_in_scroll_area(self._deep_search_page))
        self._stack.addWidget(self._wrap_in_scroll_area(self._deep_research_page))
        self._stack.addWidget(self._wrap_in_scroll_area(self._rag_page))
        self._stack.addWidget(self._wrap_in_scroll_area(self._memory_page))
        self._stack.addWidget(self._wrap_in_scroll_area(self._shortcuts_page))
        self._stack.addWidget(self._wrap_in_scroll_area(self._theme_page))


        content_layout.addWidget(self._stack)

        content_widget = QWidget()
        content_widget.setLayout(content_layout)
        main_layout.addWidget(content_widget, 1)

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
        self._sidebar.currentRowChanged.connect(self._on_category_changed)
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._save_btn.clicked.connect(self._on_save)
        self._theme_page.transparency_preview_requested.connect(
            self.transparency_preview.emit
        )
        self._viewmodel.settings_changed.connect(self._update_styles)

    def _update_styles(self) -> None:
        self.setStyleSheet(self._get_dialog_styles())
        self._apply_sidebar_icons()

    def _on_category_changed(self, row: int) -> None:
        self._stack.setCurrentIndex(row)

    def _on_cancel(self) -> None:
        self._apply_cancel()

    def _on_save(self) -> None:
        self._viewmodel.save_settings()
        self.settings_saved.emit()
        self.accept()

    def reject(self) -> None:
        self._apply_cancel()

    def _get_dialog_styles(self) -> str:
        mode = self._viewmodel.theme_mode
        c = COLORS["dark"] if mode == ThemeMode.DARK else COLORS["light"]
        p = COLORS

        base_styles = (
            get_dark_theme_stylesheet() if mode == ThemeMode.DARK else get_light_theme_stylesheet()
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
            border: 1px solid {c['border']};
        }}

        QWidget#buttonBar {{
            background-color: {c['surface']};
            border-top: 1px solid {c['border']};
        }}

        QPushButton#saveButton {{
            background-color: {p['primary']};
            color: white;
            border-radius: 6px;
            padding: 10px 18px;
            font-weight: 600;
        }}

        QPushButton#saveButton:hover {{
            background-color: {p['primary_hover']};
        }}

        QPushButton#cancelButton {{
            background-color: transparent;
            color: {c['text_secondary']};
            border: 1px solid {c['border']};
            border-radius: 6px;
            padding: 10px 18px;
        }}

        QPushButton#cancelButton:hover {{
            background-color: {c['surface_highlight']};
        }}
        """
        return f"{base_styles}\n{dialog_styles}"

    def _apply_cancel(self) -> None:
        self._viewmodel.restore_snapshot(self._initial_snapshot.copy())
        self.transparency_preview.emit(self._initial_snapshot.get("transparency", 100))
        super().reject()

    def _apply_sidebar_icons(self) -> None:
        mode = self._viewmodel.theme_mode
        c = COLORS["dark"] if mode == ThemeMode.DARK else COLORS["light"]
        normal_color = c["text_muted"]
        active_color = COLORS["primary"]

        for index, (_, _, icon_file) in enumerate(self.CATEGORIES):
            item = self._sidebar.item(index)
            if item is None:
                continue
            icon_path = self._assets_dir / icon_file
            if not icon_path.exists():
                item.setIcon(QIcon())
                continue
            base_icon = QIcon(str(icon_path))
            icon = self._build_tinted_icon(base_icon, normal_color, active_color, QSize(20, 20))
            item.setIcon(icon)

    @staticmethod
    def _build_tinted_icon(
        base_icon: QIcon,
        normal_color: str,
        active_color: str,
        size: QSize,
    ) -> QIcon:
        icon = QIcon()
        normal_pixmap = ConfigurationDialog._tint_pixmap(base_icon, normal_color, size)
        if not normal_pixmap.isNull():
            icon.addPixmap(normal_pixmap, QIcon.Mode.Normal, QIcon.State.Off)
        active_pixmap = ConfigurationDialog._tint_pixmap(base_icon, active_color, size)
        if not active_pixmap.isNull():
            icon.addPixmap(active_pixmap, QIcon.Mode.Active, QIcon.State.Off)
            icon.addPixmap(active_pixmap, QIcon.Mode.Selected, QIcon.State.Off)
        return icon

    @staticmethod
    def _tint_pixmap(icon: QIcon, color: str, size: QSize) -> QPixmap:
        pixmap = icon.pixmap(size)
        if pixmap.isNull():
            return QPixmap()
        tinted = QPixmap(pixmap.size())
        tinted.setDevicePixelRatio(pixmap.devicePixelRatio())
        tinted.fill(Qt.transparent)
        painter = QPainter(tinted)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), QColor(color))
        painter.end()
        return tinted

    @staticmethod
    def _wrap_in_scroll_area(widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(widget)
        return scroll
