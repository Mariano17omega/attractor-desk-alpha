"""Workspace repository implementation."""

from datetime import datetime
from typing import List, Optional

from ..core.models import Workspace
from .database import Database


class WorkspaceRepository:
    """SQLite implementation of workspace persistence."""
    
    def __init__(self, database: Database):
        """Initialize the repository with a database connection.
        
        Args:
            database: The workspace database manager.
        """
        self._db = database
    
    def create(self, workspace: Workspace) -> None:
        """Create a new workspace.
        
        Args:
            workspace: The workspace to create.
        """
        conn = self._db.get_connection()
        conn.execute(
            """
            INSERT INTO workspaces (id, name, created_at)
            VALUES (?, ?, ?)
            """,
            (
                workspace.id,
                workspace.name,
                workspace.created_at.isoformat(),
            ),
        )
        conn.commit()
    
    def get_by_id(self, workspace_id: str) -> Optional[Workspace]:
        """Get a workspace by ID.
        
        Args:
            workspace_id: The workspace ID to look up.
            
        Returns:
            The workspace if found, None otherwise.
        """
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
        """Get all workspaces.
        
        Returns:
            List of all workspaces.
        """
        conn = self._db.get_connection()
        cursor = conn.execute(
            """
            SELECT id, name, created_at
            FROM workspaces
            ORDER BY created_at DESC
            """
        )
        
        workspaces = []
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
        """Update an existing workspace.
        
        Args:
            workspace: The workspace with updated values.
        """
        conn = self._db.get_connection()
        conn.execute(
            """
            UPDATE workspaces
            SET name = ?
            WHERE id = ?
            """,
            (
                workspace.name,
                workspace.id,
            ),
        )
        conn.commit()
    
    def delete(self, workspace_id: str) -> None:
        """Delete a workspace and all its chats.
        
        Args:
            workspace_id: The ID of the workspace to delete.
        """
        conn = self._db.get_connection()
        # Foreign key cascade should handle chats deletion
        conn.execute(
            "DELETE FROM workspaces WHERE id = ?",
            (workspace_id,),
        )
        conn.commit()
