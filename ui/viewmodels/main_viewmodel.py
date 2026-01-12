"""Main ViewModel coordinating the application state."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot

from ui.viewmodels.chat_viewmodel import ChatViewModel
from ui.viewmodels.workspace_viewmodel import WorkspaceViewModel


class MainViewModel(QObject):
    """Main ViewModel coordinating the application state."""

    error_occurred = Signal(str)

    def __init__(
        self,
        chat_viewmodel: ChatViewModel,
        workspace_viewmodel: WorkspaceViewModel,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.chat_viewmodel = chat_viewmodel
        self.workspace_viewmodel = workspace_viewmodel
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
