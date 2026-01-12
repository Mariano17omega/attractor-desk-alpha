"""Main application window."""

import os
import subprocess
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QWidget,
)

from ..core.models import ThemeMode
from ..viewmodels import MainViewModel, SettingsViewModel
from ..infrastructure import RagService, ScreenCaptureService
from .chat_panel import ChatPanel
from .sidebar import Sidebar
from .workspace_memory_panel import WorkspaceMemoryPanel
from .styles import get_dark_theme_stylesheet, get_light_theme_stylesheet
from .configuration import ConfigurationDialog
from .region_selection_overlay import RegionSelectionOverlay
from .capture_preview_dialog import CapturePreviewDialog


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(
        self,
        viewmodel: MainViewModel,
        settings_viewmodel: Optional[SettingsViewModel] = None,
        rag_service: Optional[RagService] = None,
        screen_capture_service: Optional[ScreenCaptureService] = None,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the main window.
        
        Args:
            viewmodel: The main viewmodel.
            settings_viewmodel: Optional settings viewmodel for configuration.
            rag_service: Optional RAG service for knowledge base operations.
            screen_capture_service: Optional screen capture service.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.viewmodel = viewmodel
        self._settings_viewmodel = settings_viewmodel or SettingsViewModel()
        self._rag_service = rag_service
        self._screen_capture_service = screen_capture_service
        self._region_overlay: Optional[RegionSelectionOverlay] = None
        self._setup_ui()
        self._setup_shortcuts()
        self._connect_signals()
        self._apply_settings()
        
        # Initialize
        viewmodel.initialize()
        
        # Update RAG status if available
        if self._rag_service:
            self._sidebar.update_rag_status(self._rag_service.is_ready)
        
        # Initialize memory count
        self._update_memory_count()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        self.setWindowTitle("Attractor Desk")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        
        # Apply dark theme by default
        # self.setStyleSheet(get_dark_theme_stylesheet())
        # Handled by global app style in _apply_settings
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main layout
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Splitter for sidebar and chat
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        
        # Chat panel
        self._chat_panel = ChatPanel(
            self.viewmodel.chat_viewmodel,
            settings_viewmodel=self._settings_viewmodel,
        )
        splitter.addWidget(self._chat_panel)

        # Sidebar
        self._sidebar = Sidebar(
            self.viewmodel.workspace_viewmodel,
            self.viewmodel.workspace_memory_viewmodel,
        )
        splitter.addWidget(self._sidebar)
        
        # Workspace memory panel (hidden by default)
        self._memory_panel = WorkspaceMemoryPanel(
            self.viewmodel.workspace_memory_viewmodel
        )
        self._memory_panel.setVisible(False)
        splitter.addWidget(self._memory_panel)
        
        # Set stretch factors
        splitter.setStretchFactor(0, 1)  # Chat panel stretches
        splitter.setStretchFactor(1, 0)  # Sidebar doesn't stretch
        splitter.setStretchFactor(2, 0)  # Memory panel fixed width
        
        layout.addWidget(splitter)
        
        # Initial status
        self._update_status("Ready")

    # Status Message helper
    def _update_status(self, message: str) -> None:
        """Update the status message in the sidebar."""
        if hasattr(self, "_sidebar"):
            self._sidebar.set_status(message)

    
    def _setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts."""
        self._shortcuts: dict[str, QShortcut] = {}
        self._shortcut_actions = {
            "new_chat": self.viewmodel.new_chat,
            "new_workspace": self._on_new_workspace,
            "cancel_generation": self.viewmodel.cancel_generation,
            "open_settings": self._open_settings,
            "capture_full_screen": self._capture_full_screen,
            "capture_region": self._capture_region,
        }
        self._refresh_shortcuts()

    def _refresh_shortcuts(self) -> None:
        """Refresh shortcut bindings from settings."""
        shortcuts_by_action = {
            shortcut.action: shortcut for shortcut in self._settings_viewmodel.shortcuts
        }
        for action, handler in self._shortcut_actions.items():
            binding = shortcuts_by_action.get(action)
            if not binding:
                continue
            key_sequence = QKeySequence(binding.key_sequence)
            shortcut = self._shortcuts.get(action)
            if shortcut is None:
                shortcut = QShortcut(key_sequence, self)
                shortcut.activated.connect(handler)
                self._shortcuts[action] = shortcut
            else:
                shortcut.setKey(key_sequence)
            shortcut.setEnabled(bool(binding.key_sequence))
    
    def _connect_signals(self) -> None:
        """Connect signals to slots."""
        # Sidebar signals
        self._sidebar.new_chat_requested.connect(self.viewmodel.new_chat)
        self._sidebar.knowledge_base_requested.connect(self._open_knowledge_base)
        self._sidebar.deep_research_requested.connect(self._open_deep_research)
        self._sidebar.settings_requested.connect(self._open_settings)
        self._memory_panel.close_requested.connect(self._hide_memory_panel)
        
        # Chat panel signals
        self._chat_panel.sidebar_toggle_requested.connect(self._toggle_sidebar)
        self._chat_panel.memory_panel_requested.connect(self._toggle_memory_panel)
        
        # Memory count update
        self.viewmodel.workspace_memory_viewmodel.memories_changed.connect(
            self._update_memory_count
        )
        
        # ViewModel signals
        self.viewmodel.error_occurred.connect(self._show_error)
        
        # Chat viewmodel
        self.viewmodel.chat_viewmodel.is_loading_changed.connect(
            self._on_loading_changed
        )
        
        # Settings viewmodel
        self._settings_viewmodel.theme_changed.connect(self._apply_theme)
        self._settings_viewmodel.settings_changed.connect(self._refresh_shortcuts)
        
        # RAG service signals
        if self._rag_service:
            self._rag_service.status_changed.connect(self._on_rag_status_changed)
            self._rag_service.index_ready.connect(self._on_rag_ready)

        # Workspace memory summarization status
        self.viewmodel.workspace_memory_viewmodel.summarization_started.connect(
            self._on_summarization_started
        )
        self.viewmodel.workspace_memory_viewmodel.summarization_completed.connect(
            self._on_summarization_completed
        )
        self.viewmodel.workspace_memory_viewmodel.summarization_error.connect(
            self._on_summarization_error
        )
    
    def _apply_settings(self) -> None:
        """Apply saved settings on startup."""
        # Apply theme
        self._apply_theme(self._settings_viewmodel.theme_mode)
        
        # Apply transparency
        opacity = self._settings_viewmodel.transparency / 100.0
        self.setWindowOpacity(opacity)
        
        # Apply keep above
        if self._settings_viewmodel.keep_above:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
    
    def _apply_theme(self, mode: ThemeMode) -> None:
        """Apply the theme based on mode.
        
        Args:
            mode: The theme mode to apply.
        """
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        
        if mode == ThemeMode.LIGHT:
            app.setStyleSheet(get_light_theme_stylesheet())
        else:
            app.setStyleSheet(get_dark_theme_stylesheet())

        if hasattr(self, "_sidebar"):
            self._sidebar.apply_theme(mode)
    
    def _open_settings(self) -> None:
        """Open the settings dialog."""
        dialog = ConfigurationDialog(
            viewmodel=self._settings_viewmodel,
            rag_service=self._rag_service,
            parent=self,
        )
        dialog.transparency_preview.connect(self._preview_transparency)
        dialog.settings_saved.connect(self._on_settings_saved)
        dialog.exec()
    
    def _preview_transparency(self, value: int) -> None:
        """Preview transparency change.
        
        Args:
            value: Transparency value (30-100).
        """
        self.setWindowOpacity(value / 100.0)
    
    def _on_settings_saved(self) -> None:
        """Handle settings saved."""
        # Apply all settings
        self._apply_theme(self._settings_viewmodel.theme_mode)
        self.setWindowOpacity(self._settings_viewmodel.transparency / 100.0)
        
        # Apply keep above
        current_flags = self.windowFlags()
        if self._settings_viewmodel.keep_above:
            self.setWindowFlags(current_flags | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(current_flags & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()  # Required to apply window flags
        
        # Reconfigure RAG service with updated settings
        if self._rag_service:
            self._rag_service.configure(
                knowledge_base_path=self._settings_viewmodel.rag_knowledge_base_path,
                chunk_size=self._settings_viewmodel.rag_chunk_size,
                chunk_overlap=self._settings_viewmodel.rag_chunk_overlap,
                top_k=self._settings_viewmodel.rag_top_k,
                embedding_model=self._settings_viewmodel.rag_embedding_model,
                api_key=self._settings_viewmodel.api_key,
            )
    
    def _on_new_workspace(self) -> None:
        """Handle new workspace shortcut."""
        self._sidebar._on_new_workspace()
    
    def _on_loading_changed(self) -> None:
        """Update status bar based on loading state."""
        if self.viewmodel.chat_viewmodel.is_loading:
            self._update_status("Generating response...")
        else:
            self._update_status("Ready")

    def _on_summarization_started(self, workspace_id: str, chat_id: str) -> None:
        """Handle summarization start."""
        self._update_status("Summarizing chat...")

    def _on_summarization_completed(self, workspace_id: str, summary: str) -> None:
        """Handle summarization completion."""
        self._update_status("Workspace summary updated.")

    def _on_summarization_error(self, message: str) -> None:
        """Handle summarization error."""
        self._update_status("Summarization failed.")
    
    def _show_error(self, message: str) -> None:
        """Show an error message.
        
        Args:
            message: The error message.
        """
        QMessageBox.warning(self, "Error", message)

    def _toggle_memory_panel(self) -> None:
        """Toggle workspace memory panel visibility."""
        if self._memory_panel.isVisible():
            self._hide_memory_panel()
        else:
            self._memory_panel.setVisible(True)

    def _hide_memory_panel(self) -> None:
        """Hide the workspace memory panel."""
        self._memory_panel.setVisible(False)

    def _update_memory_count(self) -> None:
        """Update the memory button count in the chat panel."""
        count = len(self.viewmodel.workspace_memory_viewmodel.memories)
        self._chat_panel.update_memory_count(count)

    def _toggle_sidebar(self) -> None:
        """Toggle sidebar visibility."""
        if self._sidebar.isVisible():
            self._sidebar.setVisible(False)
            # Also hide memory panel if sidebar is hidden
            self._memory_panel.setVisible(False)
        else:
            self._sidebar.setVisible(True)
    
    def showEvent(self, event) -> None:
        """Handle show event."""
        super().showEvent(event)
        # Focus the input
        self._chat_panel.focus_input()
    
    def _open_knowledge_base(self) -> None:
        """Open the knowledge base folder in file manager."""
        if self._rag_service:
            self._rag_service.ensure_knowledge_base_path()
        
        kb_path = Path(self._settings_viewmodel.rag_knowledge_base_path)
        
        try:
            kb_path.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        
        if kb_path.exists():
            try:
                if os.name == "nt":  # Windows
                    os.startfile(str(kb_path))
                elif os.name == "posix":
                    subprocess.run(["xdg-open", str(kb_path)], check=False)
            except Exception:
                self._update_status(f"Could not open folder: {kb_path}")

    def _open_deep_research(self) -> None:
        """Open the Deep Research folder in file manager."""
        # Create Deep Research folder next to knowledge base
        kb_path = Path(self._settings_viewmodel.rag_knowledge_base_path)
        deep_research_path = kb_path.parent / "Deep Research"
        
        try:
            deep_research_path.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        
        if deep_research_path.exists():
            try:
                if os.name == "nt":  # Windows
                    os.startfile(str(deep_research_path))
                elif os.name == "posix":
                    subprocess.run(["xdg-open", str(deep_research_path)], check=False)
            except Exception:
                self._update_status(f"Could not open folder: {deep_research_path}")
    
    def _on_rag_status_changed(self, status: str) -> None:
        """Handle RAG status change."""
        self._sidebar.update_rag_status(False, status)
        self._update_status(status)
    
    def _on_rag_ready(self, ready: bool) -> None:
        """Handle RAG ready signal."""
        self._sidebar.update_rag_status(ready)

    def _capture_full_screen(self) -> None:
        """Trigger full-screen capture."""
        if not self._screen_capture_service:
            return
        
        if not self.viewmodel.chat_viewmodel.can_capture:
            self._show_error(
                "The current model does not support image attachments. "
                "Please select a multimodal model to use screen capture."
            )
            return
        
        # Minimize window before capture
        self.showMinimized()
        
        # Short delay to let window minimize
        from PySide6.QtCore import QTimer
        QTimer.singleShot(200, self._do_full_screen_capture)

    def _do_full_screen_capture(self) -> None:
        """Perform the full-screen capture."""
        if not self._screen_capture_service:
            return
            
        image = self._screen_capture_service.capture_full_screen()
        
        # Restore window
        self.showNormal()
        self.activateWindow()
        
        if image and not image.isNull():
            self._show_capture_preview(image)

    def _capture_region(self) -> None:
        """Trigger region capture."""
        if not self._screen_capture_service:
            return
        
        if not self.viewmodel.chat_viewmodel.can_capture:
            self._show_error(
                "The current model does not support image attachments. "
                "Please select a multimodal model to use screen capture."
            )
            return
        
        # Get monitor geometry
        monitor_rect = self._screen_capture_service.get_monitor_geometry()
        if not monitor_rect:
            self._show_error("Could not detect active monitor.")
            return
        
        # Minimize window before showing overlay
        self.showMinimized()
        
        # Short delay then show overlay
        from PySide6.QtCore import QTimer
        QTimer.singleShot(200, lambda: self._show_region_overlay(monitor_rect))

    def _show_region_overlay(self, monitor_rect) -> None:
        """Show the region selection overlay."""
        self._region_overlay = RegionSelectionOverlay(monitor_rect)
        self._region_overlay.region_selected.connect(self._on_region_selected)
        self._region_overlay.selection_cancelled.connect(self._on_region_cancelled)
        self._region_overlay.show()

    def _on_region_selected(self, rect) -> None:
        """Handle region selection completion."""
        # Ensure overlay is fully cleaned up before proceeding
        if self._region_overlay:
            self._region_overlay.deleteLater()
            self._region_overlay = None
        
        if not self._screen_capture_service:
            self._restore_after_capture()
            return
        
        image = self._screen_capture_service.capture_region(rect)
        
        # Restore window
        self._restore_after_capture()
        
        if image and not image.isNull():
            self._show_capture_preview(image)

    def _on_region_cancelled(self) -> None:
        """Handle region selection cancellation."""
        self._restore_after_capture()

    def _restore_after_capture(self) -> None:
        """Restore window after capture workflow."""
        self.showNormal()
        self.activateWindow()
        self._region_overlay = None

    def _show_capture_preview(self, image) -> None:
        """Show the capture preview dialog."""
        dialog = CapturePreviewDialog(image, parent=self)
        dialog.retake_requested.connect(self._capture_full_screen)
        
        if dialog.exec():
            # User confirmed - add to pending attachments
            final_image = dialog.get_image()
            self.viewmodel.chat_viewmodel.add_pending_attachment(final_image)
            self._update_status("Screenshot attached")
