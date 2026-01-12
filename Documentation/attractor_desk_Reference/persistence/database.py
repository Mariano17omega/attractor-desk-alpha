import sqlite3
import threading
from pathlib import Path
from typing import Optional


class Database:
    """Unified database manager for the application."""
    
    SCHEMA = """
    PRAGMA foreign_keys = ON;
    
    -- Workspaces
    CREATE TABLE IF NOT EXISTS workspaces (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    
    -- Chats
    CREATE TABLE IF NOT EXISTS chats (
        id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        title TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_chats_workspace_id ON chats(workspace_id);

    -- Messages
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        chat_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);
    CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
    
    -- Workspace Memories
    CREATE TABLE IF NOT EXISTS workspace_memories (
        id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        content TEXT NOT NULL,
        source_type TEXT NOT NULL,
        source_id TEXT,
        priority INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_workspace_memories_workspace_id
        ON workspace_memories(workspace_id);
    CREATE INDEX IF NOT EXISTS idx_workspace_memories_source_type
        ON workspace_memories(source_type);
        
    -- Agent Memories
    CREATE TABLE IF NOT EXISTS agent_memories (
        id TEXT PRIMARY KEY,
        agent_id TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_agent_memories_agent_id ON agent_memories(agent_id);
    
    -- Settings
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        category TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_settings_category ON settings(category);
    
    -- Message Attachments
    CREATE TABLE IF NOT EXISTS message_attachments (
        id TEXT PRIMARY KEY,
        message_id TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_size INTEGER NOT NULL,
        width INTEGER NOT NULL,
        height INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_message_attachments_message_id ON message_attachments(message_id);
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the database connection.
        
        Args:
            db_path: Path to the database file. If None, uses default location.
        """
        if db_path is None:
            db_path = Path.home() / ".attractor_desk" / "database.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_schema()
    
    def _init_schema(self) -> None:
        """Initialize the database schema."""
        conn = self.get_connection()
        conn.executescript(self.SCHEMA)
        conn.commit()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get or create a database connection for the current thread."""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                str(self.db_path)
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable foreign key support and WAL mode
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            self._local.connection.execute("PRAGMA journal_mode=WAL")
        return self._local.connection
    
    def close(self) -> None:
        """Close the database connection for the current thread."""
        if hasattr(self._local, "connection") and self._local.connection is not None:
            self._local.connection.close()
            self._local.connection = None
