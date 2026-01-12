"""Session repository implementation."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from core.models import Session
from .database import Database


class SessionRepository:
    """SQLite implementation of session persistence."""

    def __init__(self, database: Database):
        self._db = database

    def create(self, session: Session) -> None:
        conn = self._db.get_connection()
        conn.execute(
            """
            INSERT INTO sessions (id, workspace_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session.id,
                session.workspace_id,
                session.title,
                session.created_at.isoformat(),
                session.updated_at.isoformat(),
            ),
        )
        conn.commit()

    def get_by_id(self, session_id: str) -> Optional[Session]:
        conn = self._db.get_connection()
        cursor = conn.execute(
            """
            SELECT id, workspace_id, title, created_at, updated_at
            FROM sessions
            WHERE id = ?
            """,
            (session_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return Session(
            id=row["id"],
            workspace_id=row["workspace_id"],
            title=row["title"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def get_by_workspace(self, workspace_id: str) -> List[Session]:
        conn = self._db.get_connection()
        cursor = conn.execute(
            """
            SELECT id, workspace_id, title, created_at, updated_at
            FROM sessions
            WHERE workspace_id = ?
            ORDER BY updated_at DESC
            """,
            (workspace_id,),
        )
        sessions: List[Session] = []
        for row in cursor.fetchall():
            sessions.append(
                Session(
                    id=row["id"],
                    workspace_id=row["workspace_id"],
                    title=row["title"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
            )
        return sessions

    def update(self, session: Session) -> None:
        conn = self._db.get_connection()
        conn.execute(
            """
            UPDATE sessions
            SET title = ?, updated_at = ?
            WHERE id = ?
            """,
            (session.title, session.updated_at.isoformat(), session.id),
        )
        conn.commit()

    def delete(self, session_id: str) -> None:
        conn = self._db.get_connection()
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
