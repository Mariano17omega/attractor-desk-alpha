import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..core.models import Setting
from .database import Database


KEY_MAX_WORKSPACE_MEMORY_TOKENS = "memory.max_workspace_tokens"
DEFAULT_MAX_WORKSPACE_MEMORY_TOKENS = 1500
KEY_MEMORY_AUTO_SUMMARIZE = "memory.auto_summarize"
DEFAULT_MEMORY_AUTO_SUMMARIZE = True

# RAG configuration keys
KEY_RAG_KNOWLEDGE_BASE_PATH = "rag.knowledge_base_path"
DEFAULT_RAG_KNOWLEDGE_BASE_PATH = str(Path.home() / "Documents" / "Doc_RAG")
KEY_RAG_CHUNK_SIZE = "rag.chunk_size"
DEFAULT_RAG_CHUNK_SIZE = 1000
KEY_RAG_CHUNK_OVERLAP = "rag.chunk_overlap"
DEFAULT_RAG_CHUNK_OVERLAP = 200
KEY_RAG_TOP_K = "rag.top_k"
DEFAULT_RAG_TOP_K = 4
KEY_RAG_EMBEDDING_MODEL = "rag.embedding_model"
DEFAULT_RAG_EMBEDDING_MODEL = "openai/text-embedding-3-small"


class SettingsRepository:
    """Repository for settings persistence operations."""
    
    def __init__(self, database: Database):
        """Initialize the repository.
        
        Args:
            database: The settings database instance.
        """
        self._db = database
    
    def get(self, key: str) -> Optional[Setting]:
        """Get a setting by key.
        
        Args:
            key: The setting key.
            
        Returns:
            The setting if found, None otherwise.
        """
        conn = self._db.get_connection()
        cursor = conn.execute(
            "SELECT key, value, category, updated_at FROM settings WHERE key = ?",
            (key,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return Setting(
            key=row["key"],
            value=row["value"],
            category=row["category"],
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
    
    def get_all(self) -> list[Setting]:
        """Get all settings.
        
        Returns:
            List of all settings.
        """
        conn = self._db.get_connection()
        cursor = conn.execute(
            "SELECT key, value, category, updated_at FROM settings ORDER BY category, key"
        )
        return [
            Setting(
                key=row["key"],
                value=row["value"],
                category=row["category"],
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            for row in cursor.fetchall()
        ]
    
    def get_by_category(self, category: str) -> list[Setting]:
        """Get all settings in a category.
        
        Args:
            category: The category name.
            
        Returns:
            List of settings in the category.
        """
        conn = self._db.get_connection()
        cursor = conn.execute(
            "SELECT key, value, category, updated_at FROM settings WHERE category = ? ORDER BY key",
            (category,),
        )
        return [
            Setting(
                key=row["key"],
                value=row["value"],
                category=row["category"],
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            for row in cursor.fetchall()
        ]
    
    def set(self, key: str, value: str, category: str) -> Setting:
        """Set a setting value (upsert).
        
        Args:
            key: The setting key.
            value: The setting value.
            category: The setting category.
            
        Returns:
            The created or updated setting.
        """
        conn = self._db.get_connection()
        now = datetime.now()
        conn.execute(
            """
            INSERT INTO settings (key, value, category, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                category = excluded.category,
                updated_at = excluded.updated_at
            """,
            (key, value, category, now.isoformat()),
        )
        conn.commit()
        return Setting(key=key, value=value, category=category, updated_at=now)
    
    def delete(self, key: str) -> bool:
        """Delete a setting.
        
        Args:
            key: The setting key.
            
        Returns:
            True if deleted, False if not found.
        """
        conn = self._db.get_connection()
        cursor = conn.execute("DELETE FROM settings WHERE key = ?", (key,))
        conn.commit()
        return cursor.rowcount > 0
    
    def get_value(self, key: str, default: str = "") -> str:
        """Get a setting value with a default.
        
        Args:
            key: The setting key.
            default: Default value if not found.
            
        Returns:
            The setting value or default.
        """
        setting = self.get(key)
        return setting.value if setting else default

    def get_int(self, key: str, default: int = 0) -> int:
        """Get a setting value parsed as an int."""
        value = self.get_value(key, str(default))
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a setting value parsed as a bool."""
        value = self.get_value(key, str(default).lower())
        return value.strip().lower() in ("1", "true", "yes", "on")

    def get_max_workspace_memory_tokens(
        self, default: int = DEFAULT_MAX_WORKSPACE_MEMORY_TOKENS
    ) -> int:
        """Get the max workspace memory tokens setting."""
        return self.get_int(KEY_MAX_WORKSPACE_MEMORY_TOKENS, default)

    def get_auto_summarize(self, default: bool = DEFAULT_MEMORY_AUTO_SUMMARIZE) -> bool:
        """Get the auto-summarize setting for workspace memories."""
        return self.get_bool(KEY_MEMORY_AUTO_SUMMARIZE, default)

    def get_rag_knowledge_base_path(
        self, default: str = DEFAULT_RAG_KNOWLEDGE_BASE_PATH
    ) -> str:
        """Get the RAG knowledge base path."""
        return self.get_value(KEY_RAG_KNOWLEDGE_BASE_PATH, default)

    def get_rag_chunk_size(self, default: int = DEFAULT_RAG_CHUNK_SIZE) -> int:
        """Get the RAG chunk size for document splitting."""
        return self.get_int(KEY_RAG_CHUNK_SIZE, default)

    def get_rag_chunk_overlap(self, default: int = DEFAULT_RAG_CHUNK_OVERLAP) -> int:
        """Get the RAG chunk overlap for document splitting."""
        return self.get_int(KEY_RAG_CHUNK_OVERLAP, default)

    def get_rag_top_k(self, default: int = DEFAULT_RAG_TOP_K) -> int:
        """Get the RAG top-k retrieval count."""
        return self.get_int(KEY_RAG_TOP_K, default)

    def get_rag_embedding_model(
        self, default: str = DEFAULT_RAG_EMBEDDING_MODEL
    ) -> str:
        """Get the RAG embedding model identifier."""
        return self.get_value(KEY_RAG_EMBEDDING_MODEL, default)

