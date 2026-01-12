"""Repository for agent memory persistence."""

from datetime import datetime
from typing import List

from ..core.models import AgentMemory
from .database import Database


class AgentMemoryRepository:
    """SQLite-based repository for agent memories."""
    
    def __init__(self, database: Database):
        """Initialize the repository.
        
        Args:
            database: The message database instance.
        """
        self._db = database
    
    def add(self, memory: AgentMemory) -> None:
        """Add a memory entry.
        
        Args:
            memory: The memory to add.
        """
        conn = self._db.get_connection()
        conn.execute(
            """
            INSERT INTO agent_memories (id, agent_id, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                memory.id,
                memory.agent_id,
                memory.content,
                memory.created_at.isoformat(),
            ),
        )
        conn.commit()
    
    def get_by_agent(self, agent_id: str) -> List[AgentMemory]:
        """Get all memories for an agent.
        
        Args:
            agent_id: The agent's unique identifier.
            
        Returns:
            List of memories ordered by created_at.
        """
        conn = self._db.get_connection()
        cursor = conn.execute(
            """
            SELECT id, agent_id, content, created_at
            FROM agent_memories
            WHERE agent_id = ?
            ORDER BY created_at ASC
            """,
            (agent_id,),
        )
        
        memories = []
        for row in cursor.fetchall():
            memories.append(
                AgentMemory(
                    id=row["id"],
                    agent_id=row["agent_id"],
                    content=row["content"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            )
        return memories
    
    def delete(self, memory_id: str) -> None:
        """Delete a specific memory.
        
        Args:
            memory_id: The memory's unique identifier.
        """
        conn = self._db.get_connection()
        conn.execute(
            "DELETE FROM agent_memories WHERE id = ?",
            (memory_id,),
        )
        conn.commit()
    
    def delete_matching(self, agent_id: str, phrase: str) -> int:
        """Delete memories containing a phrase.
        
        Args:
            agent_id: The agent's unique identifier.
            phrase: The phrase to search for (case-insensitive).
            
        Returns:
            Number of memories deleted.
        """
        conn = self._db.get_connection()
        cursor = conn.execute(
            """
            DELETE FROM agent_memories
            WHERE agent_id = ? AND content LIKE ?
            """,
            (agent_id, f"%{phrase}%"),
        )
        conn.commit()
        return cursor.rowcount
    
    def clear_agent(self, agent_id: str) -> None:
        """Delete all memories for an agent.
        
        Args:
            agent_id: The agent's unique identifier.
        """
        conn = self._db.get_connection()
        conn.execute(
            "DELETE FROM agent_memories WHERE agent_id = ?",
            (agent_id,),
        )
        conn.commit()
