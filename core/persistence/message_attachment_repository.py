"""Message attachment repository implementation."""

from __future__ import annotations

from datetime import datetime
from typing import List

from core.models import MessageAttachment
from .database import Database


class MessageAttachmentRepository:
    """SQLite implementation of message attachment persistence."""

    def __init__(self, database: Database):
        self._db = database

    def add(self, attachment: MessageAttachment) -> None:
        conn = self._db.get_connection()
        conn.execute(
            """
            INSERT INTO message_attachments (id, message_id, file_path, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                attachment.id,
                attachment.message_id,
                attachment.file_path,
                attachment.created_at.isoformat(),
            ),
        )
        conn.commit()

    def get_by_message(self, message_id: str) -> List[MessageAttachment]:
        conn = self._db.get_connection()
        cursor = conn.execute(
            """
            SELECT id, message_id, file_path, created_at
            FROM message_attachments
            WHERE message_id = ?
            ORDER BY created_at ASC
            """,
            (message_id,),
        )
        attachments: List[MessageAttachment] = []
        for row in cursor.fetchall():
            attachments.append(
                MessageAttachment(
                    id=row["id"],
                    message_id=row["message_id"],
                    file_path=row["file_path"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            )
        return attachments
