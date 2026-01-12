"""Repository protocols (interfaces) for data persistence."""

from typing import Protocol, List, Optional
from .models import Message, Chat, Workspace


class MessageRepositoryProtocol(Protocol):
    """Protocol for message persistence operations."""
    
    def add(self, message: Message) -> None:
        """Add a message to the repository."""
        ...
    
    def get_by_chat(self, chat_id: str) -> List[Message]:
        """Get all messages for a chat, ordered by timestamp."""
        ...
    
    def delete_by_chat(self, chat_id: str) -> None:
        """Delete all messages for a chat."""
        ...


class ChatRepositoryProtocol(Protocol):
    """Protocol for chat persistence operations."""
    
    def create(self, chat: Chat) -> None:
        """Create a new chat."""
        ...
    
    def get_by_id(self, chat_id: str) -> Optional[Chat]:
        """Get a chat by ID."""
        ...
    
    def get_by_workspace(self, workspace_id: str) -> List[Chat]:
        """Get all chats for a workspace."""
        ...
    
    def update(self, chat: Chat) -> None:
        """Update an existing chat."""
        ...
    
    def delete(self, chat_id: str) -> None:
        """Delete a chat."""
        ...


class WorkspaceRepositoryProtocol(Protocol):
    """Protocol for workspace persistence operations."""
    
    def create(self, workspace: Workspace) -> None:
        """Create a new workspace."""
        ...
    
    def get_by_id(self, workspace_id: str) -> Optional[Workspace]:
        """Get a workspace by ID."""
        ...
    
    def get_all(self) -> List[Workspace]:
        """Get all workspaces."""
        ...
    
    def update(self, workspace: Workspace) -> None:
        """Update an existing workspace."""
        ...
    
    def delete(self, workspace_id: str) -> None:
        """Delete a workspace."""
        ...


class AgentRepositoryProtocol(Protocol):
    """Protocol for agent configuration operations."""
    
    def get_all(self) -> List["Agent"]:
        """Get all available agents."""
        ...
    
    def get_by_id(self, agent_id: str) -> Optional["Agent"]:
        """Get an agent by ID."""
        ...
    
    def get_default(self) -> Optional["Agent"]:
        """Get the default agent."""
        ...
    
    def reload(self) -> None:
        """Reload agents from configuration files."""
        ...


class AgentMemoryRepositoryProtocol(Protocol):
    """Protocol for agent memory persistence operations."""
    
    def add(self, memory: "AgentMemory") -> None:
        """Add a memory entry."""
        ...
    
    def get_by_agent(self, agent_id: str) -> List["AgentMemory"]:
        """Get all memories for an agent."""
        ...
    
    def delete(self, memory_id: str) -> None:
        """Delete a specific memory."""
        ...
    
    def delete_matching(self, agent_id: str, phrase: str) -> int:
        """Delete memories containing a phrase. Returns count deleted."""
        ...

