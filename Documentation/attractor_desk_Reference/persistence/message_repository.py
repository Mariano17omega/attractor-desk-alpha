"""Message repository implementation."""

from datetime import datetime
from typing import List, Optional, Tuple

from ..core.models import Message, MessageRole
from .database import Database

# Default page size for chat history
DEFAULT_PAGE_SIZE = 50


class MessageRepository:
    """SQLite implementation of message persistence."""
    
    def __init__(self, database: Database):
        """Initialize the repository with a database connection.
        
        Args:
            database: The message database manager.
        """
        self._db = database
    
    def add(self, message: Message) -> None:
        """Add a message to the repository.
        
        Args:
            message: The message to add.
        """
        conn = self._db.get_connection()
        conn.execute(
            """
            INSERT INTO messages (id, chat_id, role, content, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                message.id,
                message.chat_id,
                message.role.value,
                message.content,
                message.timestamp.isoformat(),
            ),
        )
        conn.commit()
    
    def get_by_chat(self, chat_id: str) -> List[Message]:
        """Get all messages for a chat, ordered by timestamp.
        
        Args:
            chat_id: The chat ID to filter by.
            
        Returns:
            List of messages ordered by timestamp.
        """
        conn = self._db.get_connection()
        cursor = conn.execute(
            """
            SELECT id, chat_id, role, content, timestamp
            FROM messages
            WHERE chat_id = ?
            ORDER BY timestamp ASC
            """,
            (chat_id,),
        )
        
        messages = []
        for row in cursor.fetchall():
            messages.append(
                Message(
                    id=row["id"],
                    chat_id=row["chat_id"],
                    role=MessageRole(row["role"]),
                    content=row["content"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                )
            )
        return messages
    
    def get_recent_page(
        self, chat_id: str, limit: int = DEFAULT_PAGE_SIZE
    ) -> Tuple[List[Message], bool]:
        """Get the most recent page of messages for a chat.
        
        Args:
            chat_id: The chat ID to filter by.
            limit: Maximum number of messages to return.
            
        Returns:
            Tuple of (messages ordered oldest to newest, has_more flag).
        """
        conn = self._db.get_connection()
        
        # Get count to determine has_more
        count_cursor = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE chat_id = ?",
            (chat_id,),
        )
        total_count = count_cursor.fetchone()[0]
        has_more = total_count > limit
        
        # Get most recent N messages (subquery to get newest, then order ASC)
        cursor = conn.execute(
            """
            SELECT id, chat_id, role, content, timestamp
            FROM (
                SELECT id, chat_id, role, content, timestamp
                FROM messages
                WHERE chat_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            )
            ORDER BY timestamp ASC
            """,
            (chat_id, limit),
        )
        
        messages = self._rows_to_messages(cursor.fetchall())
        return messages, has_more
    
    def get_older_page(
        self,
        chat_id: str,
        before_timestamp: datetime,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> Tuple[List[Message], bool]:
        """Get a page of messages older than the given timestamp.
        
        Args:
            chat_id: The chat ID to filter by.
            before_timestamp: Fetch messages older than this timestamp.
            limit: Maximum number of messages to return.
            
        Returns:
            Tuple of (messages ordered oldest to newest, has_more flag).
        """
        conn = self._db.get_connection()
        before_iso = before_timestamp.isoformat()
        
        # Get count of older messages to determine has_more
        count_cursor = conn.execute(
            """
            SELECT COUNT(*) FROM messages
            WHERE chat_id = ? AND timestamp < ?
            """,
            (chat_id, before_iso),
        )
        older_count = count_cursor.fetchone()[0]
        has_more = older_count > limit
        
        # Get the oldest N messages before the cursor (subquery then order ASC)
        cursor = conn.execute(
            """
            SELECT id, chat_id, role, content, timestamp
            FROM (
                SELECT id, chat_id, role, content, timestamp
                FROM messages
                WHERE chat_id = ? AND timestamp < ?
                ORDER BY timestamp DESC
                LIMIT ?
            )
            ORDER BY timestamp ASC
            """,
            (chat_id, before_iso, limit),
        )
        
        messages = self._rows_to_messages(cursor.fetchall())
        return messages, has_more
    
    def get_message_count(self, chat_id: str) -> int:
        """Get the total number of messages in a chat.
        
        Args:
            chat_id: The chat ID to count messages for.
            
        Returns:
            Total number of messages.
        """
        conn = self._db.get_connection()
        cursor = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE chat_id = ?",
            (chat_id,),
        )
        return cursor.fetchone()[0]
    
    def _rows_to_messages(self, rows) -> List[Message]:
        """Convert database rows to Message objects.
        
        Args:
            rows: Cursor result rows.
            
        Returns:
            List of Message objects.
        """
        messages = []
        for row in rows:
            messages.append(
                Message(
                    id=row["id"],
                    chat_id=row["chat_id"],
                    role=MessageRole(row["role"]),
                    content=row["content"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                )
            )
        return messages
    
    def delete_by_chat(self, chat_id: str) -> None:
        """Delete all messages for a chat.
        
        Args:
            chat_id: The chat ID whose messages should be deleted.
        """
        conn = self._db.get_connection()
        conn.execute(
            "DELETE FROM messages WHERE chat_id = ?",
            (chat_id,),
        )
        conn.commit()
