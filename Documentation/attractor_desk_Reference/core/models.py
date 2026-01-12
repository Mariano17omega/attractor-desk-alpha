"""Domain models for Attractor Desk."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class MessageRole(str, Enum):
    """Role of a message sender."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ThemeMode(str, Enum):
    """Theme mode for the application."""
    LIGHT = "light"
    DARK = "dark"


class MemorySourceType(str, Enum):
    """Source types for workspace memories."""
    CHAT_SUMMARY = "chat_summary"
    AGENT_MEMORY = "agent_memory"
    USER_ADDED = "user_added"


@dataclass
class Setting:
    """A configuration setting with key-value pair."""
    
    key: str
    value: str
    category: str
    updated_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def create(cls, key: str, value: str, category: str) -> "Setting":
        """Factory method to create a new setting."""
        return cls(
            key=key,
            value=value,
            category=category,
            updated_at=datetime.now(),
        )


@dataclass
class ShortcutBinding:
    """A keyboard shortcut binding."""
    
    action: str
    key_sequence: str
    description: str
    
    @classmethod
    def default_shortcuts(cls) -> list["ShortcutBinding"]:
        """Return the default keyboard shortcuts."""
        return [
            cls("send_message", "Ctrl+Return", "Send message"),
            cls("new_chat", "Ctrl+Shift+N", "Create new chat"),
            cls("new_workspace", "Ctrl+Shift+W", "Create new workspace"),
            cls("cancel_generation", "Escape", "Cancel generation"),
            cls("open_settings", "Ctrl+,", "Open settings"),
            cls("capture_full_screen", "Ctrl+Shift+S", "Capture full screen"),
            cls("capture_region", "Ctrl+Shift+G", "Capture region"),
        ]


@dataclass
class Message:
    """A single message in a chat conversation."""
    
    id: str
    chat_id: str
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def create(
        cls,
        chat_id: str,
        role: MessageRole,
        content: str,
    ) -> "Message":
        """Factory method to create a new message with auto-generated ID."""
        return cls(
            id=str(uuid.uuid4()),
            chat_id=chat_id,
            role=role,
            content=content,
            timestamp=datetime.now(),
        )


@dataclass
class Chat:
    """A chat conversation within a workspace."""
    
    id: str
    workspace_id: str
    title: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def create(cls, workspace_id: str, title: Optional[str] = None) -> "Chat":
        """Factory method to create a new chat with auto-generated ID."""
        now = datetime.now()
        return cls(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            title=title or "New Chat",
            created_at=now,
            updated_at=now,
        )


@dataclass
class Workspace:
    """A workspace containing multiple chats."""
    
    id: str
    name: str
    created_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def create(cls, name: str) -> "Workspace":
        """Factory method to create a new workspace with auto-generated ID."""
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            created_at=datetime.now(),
        )


@dataclass
class Agent:
    """A configurable chat agent with system prompt and model configuration."""
    
    id: str
    name: str
    description: str
    system_prompt: str
    is_default: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        system_prompt: str,
        is_default: bool = False,
    ) -> "Agent":
        """Factory method to create a new agent with auto-generated ID."""
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            system_prompt=system_prompt,
            is_default=is_default,
            created_at=datetime.now(),
        )


@dataclass
class AgentMemory:
    """A persistent memory entry for an agent."""
    
    id: str
    agent_id: str
    content: str
    created_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def create(cls, agent_id: str, content: str) -> "AgentMemory":
        """Factory method to create a new memory with auto-generated ID."""
        return cls(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            content=content,
            created_at=datetime.now(),
        )


@dataclass
class WorkspaceMemory:
    """A persistent memory entry scoped to a workspace."""

    id: str
    workspace_id: str
    content: str
    source_type: MemorySourceType
    source_id: Optional[str] = None
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(
        cls,
        workspace_id: str,
        content: str,
        source_type: MemorySourceType,
        source_id: Optional[str] = None,
        priority: int = 0,
    ) -> "WorkspaceMemory":
        """Factory method to create a workspace memory with auto-generated ID."""
        return cls(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            content=content,
            source_type=source_type,
            source_id=source_id,
            priority=priority,
            created_at=datetime.now(),
        )


@dataclass
class MessageAttachment:
    """An attachment associated with a message (e.g., screenshot)."""

    id: str
    message_id: str
    file_path: str
    file_size: int
    width: int
    height: int
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(
        cls,
        message_id: str,
        file_path: str,
        file_size: int,
        width: int,
        height: int,
    ) -> "MessageAttachment":
        """Factory method to create a new attachment with auto-generated ID."""
        return cls(
            id=str(uuid.uuid4()),
            message_id=message_id,
            file_path=file_path,
            file_size=file_size,
            width=width,
            height=height,
            created_at=datetime.now(),
        )
