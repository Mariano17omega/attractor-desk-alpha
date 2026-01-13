"""Main application window."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QSplitter, QWidget

from core.models import ThemeMode
from core.persistence import (
    ArtifactRepository,
    Database,
    MessageRepository,
    SessionRepository,
    WorkspaceRepository,
)
from ui.styles import get_dark_theme_stylesheet, get_light_theme_stylesheet
from ui.viewmodels.chat_viewmodel import ChatViewModel
from ui.viewmodels.main_viewmodel import MainViewModel
from ui.viewmodels.settings_viewmodel import SettingsViewModel
from ui.viewmodels.workspace_viewmodel import WorkspaceViewModel
from ui.widgets.artifact_panel import ArtifactPanel
from ui.widgets.chat_panel import ChatPanel
from ui.widgets.configuration import ConfigurationDialog
from ui.widgets.sidebar import Sidebar


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self._database = Database()
        self._settings_viewmodel = SettingsViewModel(settings_db=self._database)
        self._workspace_repository = WorkspaceRepository(self._database)
        self._session_repository = SessionRepository(self._database)
        self._message_repository = MessageRepository(self._database)
        self._artifact_repository = ArtifactRepository(self._database)

        self._workspace_viewmodel = WorkspaceViewModel(
            workspace_repository=self._workspace_repository,
            session_repository=self._session_repository,
            message_repository=self._message_repository,
            artifact_repository=self._artifact_repository,
        )
        self._chat_viewmodel = ChatViewModel(
            message_repository=self._message_repository,
            artifact_repository=self._artifact_repository,
            session_repository=self._session_repository,
            settings_viewmodel=self._settings_viewmodel,
        )
        self._main_viewmodel = MainViewModel(
            chat_viewmodel=self._chat_viewmodel,
            workspace_viewmodel=self._workspace_viewmodel,
            artifact_repository=self._artifact_repository,
        )

        self._setup_ui()
        self._setup_connections()
        self._apply_settings()

        self._main_viewmodel.initialize()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Attractor Desk")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)

        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        self._chat_panel = ChatPanel(self._chat_viewmodel)
        splitter.addWidget(self._chat_panel)

        self._sidebar = Sidebar(self._workspace_viewmodel)
        splitter.addWidget(self._sidebar)

        self._artifact_panel = ArtifactPanel(self._chat_viewmodel)
        self._artifact_panel.setVisible(False)
        splitter.addWidget(self._artifact_panel)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setStretchFactor(2, 0)

        layout.addWidget(splitter)

        self._update_status("Ready")

    def _setup_connections(self) -> None:
        self._sidebar.new_session_requested.connect(self._main_viewmodel.new_session)
        self._sidebar.settings_requested.connect(self._open_settings)

        self._chat_panel.sidebar_toggle_requested.connect(self._toggle_sidebar)
        self._chat_panel.memory_panel_requested.connect(self._toggle_artifact_panel)
        self._chat_panel.deep_search_toggle_requested.connect(self._toggle_deep_search)

        self._chat_viewmodel.status_changed.connect(self._update_status)
        self._chat_viewmodel.error_occurred.connect(self._update_error)
        self._chat_viewmodel.artifact_changed.connect(self._on_artifact_changed)

        self._settings_viewmodel.theme_changed.connect(self._apply_theme)
        self._settings_viewmodel.transparency_changed.connect(self._apply_transparency)
        self._settings_viewmodel.keep_above_changed.connect(self._apply_keep_above)
        self._settings_viewmodel.deep_search_toggled.connect(
            self._chat_panel.set_deep_search_enabled
        )

    def _apply_settings(self) -> None:
        self._apply_theme(self._settings_viewmodel.theme_mode)
        self._apply_transparency(self._settings_viewmodel.transparency)
        self._apply_keep_above(self._settings_viewmodel.keep_above)
        self._chat_panel.set_deep_search_enabled(
            self._settings_viewmodel.deep_search_enabled
        )

    def _apply_theme(self, mode: ThemeMode) -> None:
        app = QApplication.instance()
        if mode == ThemeMode.LIGHT:
            app.setStyleSheet(get_light_theme_stylesheet())
        else:
            app.setStyleSheet(get_dark_theme_stylesheet())
        self._sidebar.apply_theme(mode)

    def _apply_transparency(self, value: int) -> None:
        self.setWindowOpacity(value / 100.0)

    def _apply_keep_above(self, keep_above: bool) -> None:
        current_flags = self.windowFlags()
        if keep_above:
            self.setWindowFlags(current_flags | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(current_flags & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()

    def _open_settings(self) -> None:
        dialog = ConfigurationDialog(self._settings_viewmodel, self)
        dialog.transparency_preview.connect(self._apply_transparency)
        dialog.settings_saved.connect(self._apply_settings)
        dialog.exec()

    def _toggle_artifact_panel(self) -> None:
        self._artifact_panel.setVisible(not self._artifact_panel.isVisible())

    def _toggle_sidebar(self) -> None:
        if self._sidebar.isVisible():
            self._sidebar.setVisible(False)
            self._artifact_panel.setVisible(False)
        else:
            self._sidebar.setVisible(True)

    def _toggle_deep_search(self) -> None:
        current = self._settings_viewmodel.deep_search_enabled
        self._settings_viewmodel.deep_search_enabled = not current
        self._settings_viewmodel.save_settings()

    def _update_status(self, message: str) -> None:
        self._sidebar.set_status(message)

    def _update_error(self, message: str) -> None:
        self._sidebar.set_status(f"Error: {message}")

    def _on_artifact_changed(self) -> None:
        artifact = self._chat_viewmodel.current_artifact
        count = len(artifact.contents) if artifact and artifact.contents else 0
        self._chat_panel.update_memory_count(count)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._chat_panel.focus_input()

    def closeEvent(self, event) -> None:
        """Export artifacts on app close."""
        self._main_viewmodel.export_current_session()
        super().closeEvent(event)
