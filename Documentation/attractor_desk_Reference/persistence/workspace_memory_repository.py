"""Repository for workspace memory persistence."""

from datetime import datetime
from typing import List, Optional

from ..core.models import WorkspaceMemory, MemorySourceType
from .database import Database


class WorkspaceMemoryRepository:
    """SQLite-based repository for workspace memories."""

    def __init__(self, database: Database):
        """Initialize the repository.

        Args:
            database: The workspace database instance.
        """
        self._db = database

    def add(self, memory: WorkspaceMemory) -> None:
        """Add a workspace memory entry."""
        conn = self._db.get_connection()
        conn.execute(
            """
            INSERT INTO workspace_memories (
                id, workspace_id, content, source_type, source_id, priority, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory.id,
                memory.workspace_id,
                memory.content,
                memory.source_type.value,
                memory.source_id,
                memory.priority,
                memory.created_at.isoformat(),
            ),
        )
        conn.commit()

    def get_by_id(self, memory_id: str) -> Optional[WorkspaceMemory]:
        """Get a memory by its ID."""
        conn = self._db.get_connection()
        cursor = conn.execute(
            """
            SELECT id, workspace_id, content, source_type, source_id, priority, created_at
            FROM workspace_memories
            WHERE id = ?
            """,
            (memory_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return WorkspaceMemory(
            id=row["id"],
            workspace_id=row["workspace_id"],
            content=row["content"],
            source_type=MemorySourceType(row["source_type"]),
            source_id=row["source_id"],
            priority=row["priority"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def get_by_workspace(
        self,
        workspace_id: str,
        source_type: Optional[MemorySourceType] = None,
    ) -> List[WorkspaceMemory]:
        """Get memories for a workspace, optionally filtered by source type."""
        conn = self._db.get_connection()
        if source_type is None:
            cursor = conn.execute(
                """
                SELECT id, workspace_id, content, source_type, source_id, priority, created_at
                FROM workspace_memories
                WHERE workspace_id = ?
                ORDER BY priority DESC, created_at DESC
                """,
                (workspace_id,),
            )
        else:
            cursor = conn.execute(
                """
                SELECT id, workspace_id, content, source_type, source_id, priority, created_at
                FROM workspace_memories
                WHERE workspace_id = ? AND source_type = ?
                ORDER BY priority DESC, created_at DESC
                """,
                (workspace_id, source_type.value),
            )

        memories = []
        for row in cursor.fetchall():
            memories.append(
                WorkspaceMemory(
                    id=row["id"],
                    workspace_id=row["workspace_id"],
                    content=row["content"],
                    source_type=MemorySourceType(row["source_type"]),
                    source_id=row["source_id"],
                    priority=row["priority"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            )
        return memories

    def search(self, workspace_id: str, query: str) -> List[WorkspaceMemory]:
        """Search memories by content within a workspace."""
        conn = self._db.get_connection()
        cursor = conn.execute(
            """
            SELECT id, workspace_id, content, source_type, source_id, priority, created_at
            FROM workspace_memories
            WHERE workspace_id = ? AND content LIKE ?
            ORDER BY priority DESC, created_at DESC
            """,
            (workspace_id, f"%{query}%"),
        )
        memories = []
        for row in cursor.fetchall():
            memories.append(
                WorkspaceMemory(
                    id=row["id"],
                    workspace_id=row["workspace_id"],
                    content=row["content"],
                    source_type=MemorySourceType(row["source_type"]),
                    source_id=row["source_id"],
                    priority=row["priority"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            )
        return memories

    def update(self, memory: WorkspaceMemory) -> None:
        """Update an existing memory."""
        conn = self._db.get_connection()
        conn.execute(
            """
            UPDATE workspace_memories
            SET content = ?, source_type = ?, source_id = ?, priority = ?
            WHERE id = ?
            """,
            (
                memory.content,
                memory.source_type.value,
                memory.source_id,
                memory.priority,
                memory.id,
            ),
        )
        conn.commit()

    def delete(self, memory_id: str) -> None:
        """Delete a memory by ID."""
        conn = self._db.get_connection()
        conn.execute(
            "DELETE FROM workspace_memories WHERE id = ?",
            (memory_id,),
        )
        conn.commit()

    def delete_by_source(self, workspace_id: str, source_id: str) -> int:
        """Delete memories with a specific source ID."""
        conn = self._db.get_connection()
        cursor = conn.execute(
            """
            DELETE FROM workspace_memories
            WHERE workspace_id = ? AND source_id = ?
            """,
            (workspace_id, source_id),
        )
        conn.commit()
        return cursor.rowcount

    def get_aggregated_content(self, workspace_id: str, max_tokens: int = 1500) -> str:
        """Get formatted memory content for context injection."""
        if max_tokens <= 0:
            return ""

        memories = self.get_by_workspace(workspace_id)
        lines: list[str] = []
        total_tokens = 0

        for memory in memories:
            content = memory.content.strip()
            if not content:
                continue
            line = f"- {content}"
            token_estimate = self._estimate_tokens(line)
            if total_tokens + token_estimate > max_tokens:
                break
            lines.append(line)
            total_tokens += token_estimate

        return "\n".join(lines)

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count using a word-based heuristic."""
        words = text.split()
        return max(1, len(words))
