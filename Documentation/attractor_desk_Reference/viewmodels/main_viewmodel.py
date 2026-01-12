"""Main ViewModel coordinating the application state."""

from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot

from .chat_viewmodel import ChatViewModel
from .workspace_viewmodel import WorkspaceViewModel
from .workspace_memory_viewmodel import WorkspaceMemoryViewModel


class MainViewModel(QObject):
    """Main ViewModel coordinating the application state."""
    
    error_occurred = Signal(str)
    
    def __init__(
        self,
        chat_viewmodel: ChatViewModel,
        workspace_viewmodel: WorkspaceViewModel,
        workspace_memory_viewmodel: WorkspaceMemoryViewModel,
        parent: Optional[QObject] = None,
    ):
        """Initialize the MainViewModel.
        
        Args:
            chat_viewmodel: ViewModel for chat management.
            workspace_viewmodel: ViewModel for workspace management.
            workspace_memory_viewmodel: ViewModel for workspace memories.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self.chat_viewmodel = chat_viewmodel
        self.workspace_viewmodel = workspace_viewmodel
        self.workspace_memory_viewmodel = workspace_memory_viewmodel
        
        # Connect signals
        self._connect_signals()
    
    def _connect_signals(self) -> None:
        """Connect child viewmodel signals."""
        # When chat selection changes, load the chat
        self.workspace_viewmodel.current_chat_changed.connect(
            self._on_chat_selected
        )
        self.workspace_viewmodel.current_workspace_changed.connect(
            self._on_workspace_selected
        )
        
        # Forward errors
        self.chat_viewmodel.error_occurred.connect(self.error_occurred.emit)
        self.workspace_memory_viewmodel.error_occurred.connect(
            self.error_occurred.emit
        )
    
    def _on_chat_selected(self) -> None:
        """Handle chat selection change."""
        chat = self.workspace_viewmodel.current_chat
        if chat is not None:
            self.chat_viewmodel.load_chat(chat.id)
        else:
            self.chat_viewmodel.clear()

    def _on_workspace_selected(self) -> None:
        """Handle workspace selection change."""
        workspace = self.workspace_viewmodel.current_workspace
        if workspace is not None:
            self.workspace_memory_viewmodel.load_workspace(workspace.id)
    
    @Slot()
    def new_chat(self) -> None:
        """Create a new chat in the current workspace."""
        chat = self.workspace_viewmodel.create_chat()
        if chat:
            self.chat_viewmodel.load_chat(chat.id)
    
    @Slot(str)
    def new_workspace(self, name: str) -> None:
        """Create a new workspace.
        
        Args:
            name: The name of the workspace.
        """
        self.workspace_viewmodel.create_workspace(name)
        # Automatically create a chat in the new workspace
        self.new_chat()
    
    @Slot(str)
    def send_message(self, content: str) -> None:
        """Send a message in the current chat.
        
        Args:
            content: The message content.
        """
        self.chat_viewmodel.send_message(content)
    
    @Slot()
    def cancel_generation(self) -> None:
        """Cancel the current LLM generation."""
        self.chat_viewmodel.cancel_generation()
    
    @Slot(str)
    def delete_current_chat(self) -> None:
        """Delete the current chat."""
        chat = self.workspace_viewmodel.current_chat
        if chat:
            self.workspace_viewmodel.delete_chat(chat.id)
    
    def initialize(self) -> None:
        """Initialize the application state.
        
        Should be called after the UI is ready.
        """
        # Ensure there's at least one workspace
        if not self.workspace_viewmodel.workspaces:
            self.new_workspace("Default Workspace")
        
        # Ensure there's at least one chat
        else:
            workspace = self.workspace_viewmodel.current_workspace
            if workspace and not self.workspace_viewmodel.chats:
                self.new_chat()
            elif self.workspace_viewmodel.chats:
                # Select the first chat
                first_chat = self.workspace_viewmodel.chats[0]
                self.workspace_viewmodel.select_chat(first_chat.id)

        workspace = self.workspace_viewmodel.current_workspace
        if workspace:
            self.workspace_memory_viewmodel.load_workspace(workspace.id)
