"""Message repository implementation."""

from __future__ import annotations

from datetime import datetime
from typing import List

from core.models import Message, MessageRole
from .database import Database


class MessageRepository:
    """SQLite implementation of message persistence."""

    def __init__(self, database: Database):
        self._db = database

    def add(self, message: Message) -> None:
        conn = self._db.get_connection()
        conn.execute(
            """
            INSERT INTO messages (id, session_id, role, content, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                message.id,
                message.session_id,
                message.role.value,
                message.content,
                message.timestamp.isoformat(),
            ),
        )
        conn.commit()

    def get_by_session(self, session_id: str) -> List[Message]:
        conn = self._db.get_connection()
        cursor = conn.execute(
            """
            SELECT id, session_id, role, content, timestamp
            FROM messages
            WHERE session_id = ?
            ORDER BY timestamp ASC
            """,
            (session_id,),
        )
        messages: List[Message] = []
        for row in cursor.fetchall():
            messages.append(
                Message(
                    id=row["id"],
                    session_id=row["session_id"],
                    role=MessageRole(row["role"]),
                    content=row["content"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                )
            )
        return messages

    def delete_by_session(self, session_id: str) -> None:
        conn = self._db.get_connection()
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.commit()
