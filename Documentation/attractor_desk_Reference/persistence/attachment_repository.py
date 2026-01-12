"""Attachment repository implementation."""

from datetime import datetime
from typing import List

from ..core.models import MessageAttachment
from .database import Database


class AttachmentRepository:
    """SQLite implementation of message attachment persistence."""

    def __init__(self, database: Database):
        """Initialize the repository with a database connection.

        Args:
            database: The database manager.
        """
        self._db = database

    def add(self, attachment: MessageAttachment) -> None:
        """Add an attachment to the repository.

        Args:
            attachment: The attachment to add.
        """
        conn = self._db.get_connection()
        conn.execute(
            """
            INSERT INTO message_attachments 
                (id, message_id, file_path, file_size, width, height, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attachment.id,
                attachment.message_id,
                attachment.file_path,
                attachment.file_size,
                attachment.width,
                attachment.height,
                attachment.created_at.isoformat(),
            ),
        )
        conn.commit()

    def get_by_message(self, message_id: str) -> List[MessageAttachment]:
        """Get all attachments for a message.

        Args:
            message_id: The message ID to filter by.

        Returns:
            List of attachments for the message.
        """
        conn = self._db.get_connection()
        cursor = conn.execute(
            """
            SELECT id, message_id, file_path, file_size, width, height, created_at
            FROM message_attachments
            WHERE message_id = ?
            ORDER BY created_at ASC
            """,
            (message_id,),
        )

        attachments = []
        for row in cursor.fetchall():
            attachments.append(
                MessageAttachment(
                    id=row["id"],
                    message_id=row["message_id"],
                    file_path=row["file_path"],
                    file_size=row["file_size"],
                    width=row["width"],
                    height=row["height"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            )
        return attachments

    def delete_by_message(self, message_id: str) -> None:
        """Delete all attachments for a message.

        Args:
            message_id: The message ID whose attachments should be deleted.
        """
        conn = self._db.get_connection()
        conn.execute(
            "DELETE FROM message_attachments WHERE message_id = ?",
            (message_id,),
        )
        conn.commit()

    def get_all_file_paths(self) -> List[str]:
        """Get all attachment file paths in the database.

        Returns:
            List of file paths for all attachments.
        """
        conn = self._db.get_connection()
        cursor = conn.execute("SELECT file_path FROM message_attachments")
        return [row["file_path"] for row in cursor.fetchall()]

    def delete_by_id(self, attachment_id: str) -> None:
        """Delete an attachment by its ID.

        Args:
            attachment_id: The attachment ID to delete.
        """
        conn = self._db.get_connection()
        conn.execute(
            "DELETE FROM message_attachments WHERE id = ?",
            (attachment_id,),
        )
        conn.commit()
