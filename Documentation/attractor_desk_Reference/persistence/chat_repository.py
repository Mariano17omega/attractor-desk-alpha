"""Chat repository implementation."""

from datetime import datetime
from typing import List, Optional

from ..core.models import Chat
from .database import Database


class ChatRepository:
    """SQLite implementation of chat persistence."""
    
    def __init__(self, database: Database):
        """Initialize the repository with a database connection.
        
        Args:
            database: The workspace database manager.
        """
        self._db = database
    
    def create(self, chat: Chat) -> None:
        """Create a new chat.
        
        Args:
            chat: The chat to create.
        """
        conn = self._db.get_connection()
        conn.execute(
            """
            INSERT INTO chats (id, workspace_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                chat.id,
                chat.workspace_id,
                chat.title,
                chat.created_at.isoformat(),
                chat.updated_at.isoformat(),
            ),
        )
        conn.commit()
    
    def get_by_id(self, chat_id: str) -> Optional[Chat]:
        """Get a chat by ID.
        
        Args:
            chat_id: The chat ID to look up.
            
        Returns:
            The chat if found, None otherwise.
        """
        conn = self._db.get_connection()
        cursor = conn.execute(
            """
            SELECT id, workspace_id, title, created_at, updated_at
            FROM chats
            WHERE id = ?
            """,
            (chat_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        
        return Chat(
            id=row["id"],
            workspace_id=row["workspace_id"],
            title=row["title"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
    
    def get_by_workspace(self, workspace_id: str) -> List[Chat]:
        """Get all chats for a workspace.
        
        Args:
            workspace_id: The workspace ID to filter by.
            
        Returns:
            List of chats for the workspace.
        """
        conn = self._db.get_connection()
        cursor = conn.execute(
            """
            SELECT id, workspace_id, title, created_at, updated_at
            FROM chats
            WHERE workspace_id = ?
            ORDER BY updated_at DESC
            """,
            (workspace_id,),
        )
        
        chats = []
        for row in cursor.fetchall():
            chats.append(
                Chat(
                    id=row["id"],
                    workspace_id=row["workspace_id"],
                    title=row["title"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
            )
        return chats
    
    def update(self, chat: Chat) -> None:
        """Update an existing chat.
        
        Args:
            chat: The chat with updated values.
        """
        conn = self._db.get_connection()
        conn.execute(
            """
            UPDATE chats
            SET title = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                chat.title,
                chat.updated_at.isoformat(),
                chat.id,
            ),
        )
        conn.commit()
    
    def delete(self, chat_id: str) -> None:
        """Delete a chat.
        
        Args:
            chat_id: The ID of the chat to delete.
        """
        conn = self._db.get_connection()
        conn.execute(
            "DELETE FROM chats WHERE id = ?",
            (chat_id,),
        )
        conn.commit()
