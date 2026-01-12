"""Workspace ViewModel for managing workspaces and chats."""

from typing import List, Optional

from PySide6.QtCore import QObject, Signal, Property, Slot

from ..core.models import Workspace, Chat
from ..persistence import WorkspaceRepository, ChatRepository, MessageRepository


class WorkspaceViewModel(QObject):
    """ViewModel for workspace and chat list management."""
    
    workspaces_changed = Signal()
    chats_changed = Signal()
    current_workspace_changed = Signal()
    current_chat_changed = Signal()
    
    def __init__(
        self,
        workspace_repository: WorkspaceRepository,
        chat_repository: ChatRepository,
        message_repository: MessageRepository,
        parent: Optional[QObject] = None,
    ):
        """Initialize the WorkspaceViewModel.
        
        Args:
            workspace_repository: Repository for workspace persistence.
            chat_repository: Repository for chat persistence.
            message_repository: Repository for message persistence (for cascading delete).
            parent: Parent QObject.
        """
        super().__init__(parent)
        self._workspace_repository = workspace_repository
        self._chat_repository = chat_repository
        self._message_repository = message_repository
        
        self._workspaces: List[Workspace] = []
        self._chats: List[Chat] = []
        self._current_workspace: Optional[Workspace] = None
        self._current_chat: Optional[Chat] = None
        
        # Load initial data
        self._load_workspaces()
    
    @Property(list, notify=workspaces_changed)
    def workspaces(self) -> List[Workspace]:
        """Get all workspaces."""
        return self._workspaces
    
    @Property(list, notify=chats_changed)
    def chats(self) -> List[Chat]:
        """Get chats for the current workspace."""
        return self._chats
    
    @Property(object, notify=current_workspace_changed)
    def current_workspace(self) -> Optional[Workspace]:
        """Get the current workspace."""
        return self._current_workspace
    
    @Property(object, notify=current_chat_changed)
    def current_chat(self) -> Optional[Chat]:
        """Get the current chat."""
        return self._current_chat
    
    def _load_workspaces(self) -> None:
        """Load all workspaces from the repository."""
        self._workspaces = self._workspace_repository.get_all()
        self.workspaces_changed.emit()
        
        # Select first workspace if available
        if self._workspaces and self._current_workspace is None:
            self.select_workspace(self._workspaces[0].id)
    
    def _load_chats(self) -> None:
        """Load chats for the current workspace."""
        if self._current_workspace is None:
            self._chats = []
        else:
            self._chats = self._chat_repository.get_by_workspace(
                self._current_workspace.id
            )
        self.chats_changed.emit()
    
    @Slot(str)
    def select_workspace(self, workspace_id: str) -> None:
        """Select a workspace by ID.
        
        Args:
            workspace_id: The ID of the workspace to select.
        """
        workspace = self._workspace_repository.get_by_id(workspace_id)
        if workspace is None:
            return
        
        self._current_workspace = workspace
        self._current_chat = None
        self.current_workspace_changed.emit()
        self.current_chat_changed.emit()
        self._load_chats()
    
    @Slot(str)
    def select_chat(self, chat_id: str) -> None:
        """Select a chat by ID.
        
        Args:
            chat_id: The ID of the chat to select.
        """
        chat = self._chat_repository.get_by_id(chat_id)
        if chat is None:
            return
        
        self._current_chat = chat
        self.current_chat_changed.emit()
    
    @Slot(str)
    def create_workspace(self, name: str) -> None:
        """Create a new workspace.
        
        Args:
            name: The name of the workspace.
        """
        if not name.strip():
            return
        
        workspace = Workspace.create(name.strip())
        self._workspace_repository.create(workspace)
        self._workspaces.insert(0, workspace)
        self.workspaces_changed.emit()
        
        # Select the new workspace
        self.select_workspace(workspace.id)
    
    @Slot(str)
    def delete_workspace(self, workspace_id: str) -> None:
        """Delete a workspace and all its chats.
        
        Args:
            workspace_id: The ID of the workspace to delete.
        """
        # Delete all messages for all chats in this workspace
        chats = self._chat_repository.get_by_workspace(workspace_id)
        for chat in chats:
            self._message_repository.delete_by_chat(chat.id)
        
        # Delete the workspace (cascades to chats via FK)
        self._workspace_repository.delete(workspace_id)
        
        # Update state
        self._workspaces = [w for w in self._workspaces if w.id != workspace_id]
        self.workspaces_changed.emit()
        
        # Select first remaining workspace or clear
        if self._current_workspace and self._current_workspace.id == workspace_id:
            self._current_workspace = None
            self._current_chat = None
            self._chats = []
            self.current_workspace_changed.emit()
            self.current_chat_changed.emit()
            self.chats_changed.emit()
            
            if self._workspaces:
                self.select_workspace(self._workspaces[0].id)
    
    @Slot()
    def create_chat(self) -> Optional[Chat]:
        """Create a new chat in the current workspace.
        
        Returns:
            The created chat, or None if no workspace is selected.
        """
        if self._current_workspace is None:
            return None
        
        chat = Chat.create(self._current_workspace.id)
        self._chat_repository.create(chat)
        self._chats.insert(0, chat)
        self.chats_changed.emit()
        
        # Select the new chat
        self._current_chat = chat
        self.current_chat_changed.emit()
        
        return chat
    
    @Slot(str)
    def delete_chat(self, chat_id: str) -> None:
        """Delete a chat and all its messages.
        
        Args:
            chat_id: The ID of the chat to delete.
        """
        # Delete messages first
        self._message_repository.delete_by_chat(chat_id)
        
        # Delete the chat
        self._chat_repository.delete(chat_id)
        
        # Update state
        self._chats = [c for c in self._chats if c.id != chat_id]
        self.chats_changed.emit()
        
        # Clear current chat if it was deleted
        if self._current_chat and self._current_chat.id == chat_id:
            self._current_chat = None
            self.current_chat_changed.emit()
    
    def refresh(self) -> None:
        """Refresh all data from repositories."""
        self._load_workspaces()
        if self._current_workspace:
            self._load_chats()
