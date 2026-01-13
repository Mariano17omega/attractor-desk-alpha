"""Main ViewModel coordinating the application state."""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot

from core.persistence import ArtifactRepository
from core.services.artifact_export_service import ArtifactExportService
from ui.viewmodels.chat_viewmodel import ChatViewModel
from ui.viewmodels.workspace_viewmodel import WorkspaceViewModel

logger = logging.getLogger(__name__)


class MainViewModel(QObject):
    """Main ViewModel coordinating the application state."""

    error_occurred = Signal(str)

    def __init__(
        self,
        chat_viewmodel: ChatViewModel,
        workspace_viewmodel: WorkspaceViewModel,
        artifact_repository: ArtifactRepository,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.chat_viewmodel = chat_viewmodel
        self.workspace_viewmodel = workspace_viewmodel
        self._export_service = ArtifactExportService(artifact_repository)
        self._connect_signals()

    def _connect_signals(self) -> None:
        self.workspace_viewmodel.current_session_changed.connect(
            self._on_session_selected
        )
        self.workspace_viewmodel.current_workspace_changed.connect(
            self._on_workspace_selected
        )
        self.chat_viewmodel.session_updated.connect(self.workspace_viewmodel.refresh_sessions)
        self.chat_viewmodel.error_occurred.connect(self.error_occurred.emit)

    def _on_session_selected(self) -> None:
        # Export previous session before switching
        self.export_current_session()

        session = self.workspace_viewmodel.current_session
        if session is not None:
            self.chat_viewmodel.load_session(session.id)
        else:
            self.chat_viewmodel.clear()

    def _on_workspace_selected(self) -> None:
        workspace = self.workspace_viewmodel.current_workspace
        if workspace and not self.workspace_viewmodel.sessions:
            session = self.workspace_viewmodel.create_session()
            if session:
                self.chat_viewmodel.load_session(session.id)

    @Slot()
    def new_session(self) -> None:
        # Export current session before creating new one
        self.export_current_session()

        session = self.workspace_viewmodel.create_session()
        if session:
            self.chat_viewmodel.load_session(session.id)

    @Slot(str)
    def new_workspace(self, name: str) -> None:
        self.workspace_viewmodel.create_workspace(name)
        self.new_session()

    def initialize(self) -> None:
        if not self.workspace_viewmodel.workspaces:
            self.new_workspace("Default Workspace")
            return

        if not self.workspace_viewmodel.sessions:
            self.new_session()
            return

        first_session = self.workspace_viewmodel.sessions[0]
        self.workspace_viewmodel.select_session(first_session.id)

    def export_current_session(self) -> None:
        """Export artifacts from the current session to disk."""
        session_id = self.chat_viewmodel.current_session_id
        if not session_id:
            return

        # Get session title for naming
        session = self.workspace_viewmodel.current_session
        session_title = session.title if session else "Untitled"

        try:
            exported = self._export_service.export_session(session_id, session_title)
            if exported:
                logger.info("Exported %d artifacts from session %s", len(exported), session_id)
        except Exception as e:
            logger.error("Failed to export session artifacts: %s", e)

