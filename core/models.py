"""Domain models for persisted UI state."""

from __future__ import annotations

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


@dataclass
class Setting:
    """A configuration setting."""

    key: str
    value: str
    category: str
    updated_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(cls, key: str, value: str, category: str) -> "Setting":
        """Create a new setting."""
        return cls(
            key=key,
            value=value,
            category=category,
            updated_at=datetime.now(),
        )


@dataclass
class Workspace:
    """A workspace containing multiple sessions."""

    id: str
    name: str
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(cls, name: str) -> "Workspace":
        """Create a new workspace with an auto-generated ID."""
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            created_at=datetime.now(),
        )


@dataclass
class Session:
    """A chat session within a workspace."""

    id: str
    workspace_id: str
    title: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(cls, workspace_id: str, title: Optional[str] = None) -> "Session":
        """Create a new session with an auto-generated ID."""
        now = datetime.now()
        return cls(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            title=title or "New Session",
            created_at=now,
            updated_at=now,
        )


@dataclass
class Message:
    """A single message in a session."""

    id: str
    session_id: str
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(
        cls,
        session_id: str,
        role: MessageRole,
        content: str,
    ) -> "Message":
        """Create a message with an auto-generated ID."""
        return cls(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            timestamp=datetime.now(),
        )
