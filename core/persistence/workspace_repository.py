"""Workspace repository implementation."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from core.models import Workspace
from .database import Database


class WorkspaceRepository:
    """SQLite implementation of workspace persistence."""

    def __init__(self, database: Database):
        self._db = database

    def create(self, workspace: Workspace) -> None:
        conn = self._db.get_connection()
        conn.execute(
            """
            INSERT INTO workspaces (id, name, created_at)
            VALUES (?, ?, ?)
            """,
            (workspace.id, workspace.name, workspace.created_at.isoformat()),
        )
        conn.commit()

    def get_by_id(self, workspace_id: str) -> Optional[Workspace]:
        conn = self._db.get_connection()
        cursor = conn.execute(
            """
            SELECT id, name, created_at
            FROM workspaces
            WHERE id = ?
            """,
            (workspace_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return Workspace(
            id=row["id"],
            name=row["name"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def get_all(self) -> List[Workspace]:
        conn = self._db.get_connection()
        cursor = conn.execute(
            """
            SELECT id, name, created_at
            FROM workspaces
            ORDER BY created_at DESC
            """
        )
        workspaces: List[Workspace] = []
        for row in cursor.fetchall():
            workspaces.append(
                Workspace(
                    id=row["id"],
                    name=row["name"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            )
        return workspaces

    def update(self, workspace: Workspace) -> None:
        conn = self._db.get_connection()
        conn.execute(
            """
            UPDATE workspaces
            SET name = ?
            WHERE id = ?
            """,
            (workspace.name, workspace.id),
        )
        conn.commit()

    def delete(self, workspace_id: str) -> None:
        conn = self._db.get_connection()
        conn.execute(
            "DELETE FROM workspaces WHERE id = ?",
            (workspace_id,),
        )
        conn.commit()
