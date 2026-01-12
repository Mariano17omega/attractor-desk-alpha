"""Workspace ViewModel for managing workspaces and sessions."""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QObject, Signal, Property, Slot

from core.models import Workspace, Session
from core.persistence import ArtifactRepository, MessageRepository, SessionRepository, WorkspaceRepository


class WorkspaceViewModel(QObject):
    """ViewModel for workspace and session list management."""

    workspaces_changed = Signal()
    sessions_changed = Signal()
    current_workspace_changed = Signal()
    current_session_changed = Signal()

    def __init__(
        self,
        workspace_repository: WorkspaceRepository,
        session_repository: SessionRepository,
        message_repository: MessageRepository,
        artifact_repository: ArtifactRepository,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._workspace_repository = workspace_repository
        self._session_repository = session_repository
        self._message_repository = message_repository
        self._artifact_repository = artifact_repository

        self._workspaces: List[Workspace] = []
        self._sessions: List[Session] = []
        self._current_workspace: Optional[Workspace] = None
        self._current_session: Optional[Session] = None

        self._load_workspaces()

    @Property(list, notify=workspaces_changed)
    def workspaces(self) -> List[Workspace]:
        return self._workspaces

    @Property(list, notify=sessions_changed)
    def sessions(self) -> List[Session]:
        return self._sessions

    @Property(object, notify=current_workspace_changed)
    def current_workspace(self) -> Optional[Workspace]:
        return self._current_workspace

    @Property(object, notify=current_session_changed)
    def current_session(self) -> Optional[Session]:
        return self._current_session

    def _load_workspaces(self) -> None:
        self._workspaces = self._workspace_repository.get_all()
        self.workspaces_changed.emit()

        if self._workspaces and self._current_workspace is None:
            self.select_workspace(self._workspaces[0].id)

    def _load_sessions(self) -> None:
        if self._current_workspace is None:
            self._sessions = []
        else:
            self._sessions = self._session_repository.get_by_workspace(
                self._current_workspace.id
            )
        self.sessions_changed.emit()

    @Slot(str)
    def select_workspace(self, workspace_id: str) -> None:
        workspace = self._workspace_repository.get_by_id(workspace_id)
        if workspace is None:
            return
        self._current_workspace = workspace
        self._current_session = None
        self.current_workspace_changed.emit()
        self.current_session_changed.emit()
        self._load_sessions()

    @Slot(str)
    def select_session(self, session_id: str) -> None:
        session = self._session_repository.get_by_id(session_id)
        if session is None:
            return
        self._current_session = session
        self.current_session_changed.emit()

    @Slot(str)
    def create_workspace(self, name: str) -> None:
        if not name.strip():
            return
        workspace = Workspace.create(name.strip())
        self._workspace_repository.create(workspace)
        self._workspaces.insert(0, workspace)
        self.workspaces_changed.emit()
        self.select_workspace(workspace.id)

    @Slot(str)
    def delete_workspace(self, workspace_id: str) -> None:
        self._workspace_repository.delete(workspace_id)
        self._workspaces = [w for w in self._workspaces if w.id != workspace_id]
        self.workspaces_changed.emit()

        if self._current_workspace and self._current_workspace.id == workspace_id:
            self._current_workspace = None
            self._current_session = None
            self._sessions = []
            self.current_workspace_changed.emit()
            self.current_session_changed.emit()
            self.sessions_changed.emit()

            if self._workspaces:
                self.select_workspace(self._workspaces[0].id)

    @Slot()
    def create_session(self) -> Optional[Session]:
        if self._current_workspace is None:
            return None
        session = Session.create(self._current_workspace.id)
        self._session_repository.create(session)
        self._sessions.insert(0, session)
        self.sessions_changed.emit()
        self._current_session = session
        self.current_session_changed.emit()
        return session

    @Slot(str)
    def delete_session(self, session_id: str) -> None:
        self._message_repository.delete_by_session(session_id)
        self._artifact_repository.delete_by_session(session_id)
        self._session_repository.delete(session_id)
        self._sessions = [s for s in self._sessions if s.id != session_id]
        self.sessions_changed.emit()

        if self._current_session and self._current_session.id == session_id:
            self._current_session = None
            self.current_session_changed.emit()

    def refresh(self) -> None:
        self._load_workspaces()
        if self._current_workspace:
            self._load_sessions()

    def refresh_sessions(self) -> None:
        if self._current_workspace:
            self._load_sessions()
