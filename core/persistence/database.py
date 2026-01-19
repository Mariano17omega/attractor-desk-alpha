"""SQLite database manager for persisted UI state."""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
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

    -- Sessions
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        title TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_sessions_workspace_id ON sessions(workspace_id);

    -- Messages
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
    CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);

    -- Message attachments
    CREATE TABLE IF NOT EXISTS message_attachments (
        id TEXT PRIMARY KEY,
        message_id TEXT NOT NULL,
        file_path TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_message_attachments_message_id
        ON message_attachments(message_id);

    -- Artifacts
    CREATE TABLE IF NOT EXISTS artifacts (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL UNIQUE,
        artifact_json TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_artifacts_session_id ON artifacts(session_id);

    -- RAG documents
    CREATE TABLE IF NOT EXISTS rag_documents (
        id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        artifact_entry_id TEXT,
        source_type TEXT NOT NULL,
        source_name TEXT NOT NULL,
        source_path TEXT,
        content_hash TEXT NOT NULL,
        indexed_at TEXT,
        file_size INTEGER,
        embedding_status TEXT NOT NULL DEFAULT 'disabled',
        embedding_model TEXT,
        embedding_error TEXT,
        stale_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_rag_documents_workspace_id ON rag_documents(workspace_id);

    -- RAG document/session attachments
    CREATE TABLE IF NOT EXISTS rag_document_sessions (
        document_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (document_id, session_id),
        FOREIGN KEY (document_id) REFERENCES rag_documents(id) ON DELETE CASCADE,
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_rag_doc_sessions_session_id ON rag_document_sessions(session_id);

    -- RAG chunks
    CREATE TABLE IF NOT EXISTS rag_chunks (
        id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        section_title TEXT,
        content TEXT NOT NULL,
        token_count INTEGER,
        created_at TEXT NOT NULL,
        FOREIGN KEY (document_id) REFERENCES rag_documents(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_rag_chunks_document_id ON rag_chunks(document_id);

    -- RAG lexical search
    CREATE VIRTUAL TABLE IF NOT EXISTS rag_chunks_fts USING fts5(
        chunk_id UNINDEXED,
        content,
        section_title,
        source_name
    );

    -- RAG embeddings
    CREATE TABLE IF NOT EXISTS rag_embeddings (
        chunk_id TEXT PRIMARY KEY,
        model TEXT NOT NULL,
        dims INTEGER NOT NULL,
        embedding_blob BLOB NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (chunk_id) REFERENCES rag_chunks(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_rag_embeddings_model ON rag_embeddings(model);

    -- RAG indexing registry
    CREATE TABLE IF NOT EXISTS rag_index_registry (
        source_path TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        status TEXT NOT NULL,
        retry_count INTEGER NOT NULL,
        last_seen_at TEXT,
        last_indexed_at TEXT,
        error_message TEXT,
        embedding_model TEXT,
        embedding_status TEXT,
        embedding_error TEXT,
        PRIMARY KEY (source_path, content_hash)
    );

    -- Settings
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        category TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_settings_category ON settings(category);
    """

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path.home() / ".attractor_desk" / "database.db"
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_schema()

    def _init_schema(self) -> None:
        conn = self.get_connection()
        conn.executescript(self.SCHEMA)
        self._apply_migrations(conn)
        conn.commit()

    def _apply_migrations(self, conn: sqlite3.Connection) -> None:
        self._ensure_rag_document_columns(conn)
        self._ensure_rag_index_registry(conn)
        self._seed_global_workspace(conn)

    # Allowlist for migration column validation (Issue #3: Dynamic SQL safety)
    _RAG_DOCUMENT_MIGRATION_COLUMNS: frozenset = frozenset({
        "indexed_at",
        "file_size",
        "embedding_status",
        "embedding_model",
        "embedding_error",
        "stale_at",
    })
    _RAG_DOCUMENT_MIGRATION_TYPES: frozenset = frozenset({
        "TEXT",
        "INTEGER",
        "TEXT NOT NULL DEFAULT 'disabled'",
    })

    def _ensure_rag_document_columns(self, conn: sqlite3.Connection) -> None:
        cursor = conn.execute("PRAGMA table_info(rag_documents)")
        existing = {row["name"] for row in cursor.fetchall()}
        embedding_status_added = "embedding_status" not in existing
        embedding_model_added = "embedding_model" not in existing

        # Hardcoded migration columns with explicit allowlist validation
        columns = {
            "indexed_at": "TEXT",
            "file_size": "INTEGER",
            "embedding_status": "TEXT NOT NULL DEFAULT 'disabled'",
            "embedding_model": "TEXT",
            "embedding_error": "TEXT",
            "stale_at": "TEXT",
        }

        for name, col_type in columns.items():
            # Validate against allowlist before executing dynamic SQL
            if name not in self._RAG_DOCUMENT_MIGRATION_COLUMNS:
                raise ValueError(f"Migration blocked: unknown column '{name}'")
            if col_type not in self._RAG_DOCUMENT_MIGRATION_TYPES:
                raise ValueError(f"Migration blocked: unknown type '{col_type}'")
            if name not in existing:
                conn.execute(f"ALTER TABLE rag_documents ADD COLUMN {name} {col_type}")
        conn.execute(
            """
            UPDATE rag_documents
            SET indexed_at = created_at
            WHERE indexed_at IS NULL
            """
        )
        if embedding_status_added:
            conn.execute(
                """
                UPDATE rag_documents
                SET embedding_status = 'indexed',
                    embedding_model = COALESCE(
                        embedding_model,
                        (
                            SELECT e.model
                            FROM rag_embeddings e
                            JOIN rag_chunks c ON c.id = e.chunk_id
                            WHERE c.document_id = rag_documents.id
                            LIMIT 1
                        )
                    )
                WHERE embedding_status = 'disabled'
                  AND EXISTS (
                    SELECT 1
                    FROM rag_embeddings e
                    JOIN rag_chunks c ON c.id = e.chunk_id
                    WHERE c.document_id = rag_documents.id
                )
                """
            )
        elif embedding_model_added:
            conn.execute(
                """
                UPDATE rag_documents
                SET embedding_model = COALESCE(
                    embedding_model,
                    (
                        SELECT e.model
                        FROM rag_embeddings e
                        JOIN rag_chunks c ON c.id = e.chunk_id
                        WHERE c.document_id = rag_documents.id
                        LIMIT 1
                    )
                )
                WHERE embedding_status = 'indexed'
                  AND embedding_model IS NULL
                  AND EXISTS (
                    SELECT 1
                    FROM rag_embeddings e
                    JOIN rag_chunks c ON c.id = e.chunk_id
                    WHERE c.document_id = rag_documents.id
                )
                """
            )

    def _ensure_rag_index_registry(self, conn: sqlite3.Connection) -> None:
        cursor = conn.execute("PRAGMA table_info(rag_index_registry)")
        existing = {row["name"] for row in cursor.fetchall()}
        embedding_status_added = "embedding_status" not in existing
        if "embedding_model" not in existing:
            conn.execute(
                "ALTER TABLE rag_index_registry ADD COLUMN embedding_model TEXT"
            )
        if "embedding_status" not in existing:
            conn.execute(
                "ALTER TABLE rag_index_registry ADD COLUMN embedding_status TEXT"
            )
        if "embedding_error" not in existing:
            conn.execute(
                "ALTER TABLE rag_index_registry ADD COLUMN embedding_error TEXT"
            )
        if embedding_status_added:
            conn.execute(
                """
                UPDATE rag_index_registry
                SET embedding_status = 'indexed'
                WHERE embedding_status IS NULL
                  AND EXISTS (
                    SELECT 1
                    FROM rag_documents d
                    JOIN rag_chunks c ON c.document_id = d.id
                    JOIN rag_embeddings e ON e.chunk_id = c.id
                    WHERE d.source_path = rag_index_registry.source_path
                      AND d.content_hash = rag_index_registry.content_hash
                )
                """
            )
            conn.execute(
                """
                UPDATE rag_index_registry
                SET embedding_status = 'disabled'
                WHERE embedding_status IS NULL
                """
            )

    def _seed_global_workspace(self, conn: sqlite3.Connection) -> None:
        now = datetime.now().isoformat()
        conn.execute(
            """
            INSERT OR IGNORE INTO workspaces (id, name, created_at)
            VALUES (?, ?, ?)
            """,
            ("GLOBAL", "Global", now),
        )

    def get_connection(self) -> sqlite3.Connection:
        """Get or create a database connection for the current thread."""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._local.connection = sqlite3.connect(str(self.db_path))
            self._local.connection.row_factory = sqlite3.Row
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            self._local.connection.execute("PRAGMA journal_mode=WAL")
        return self._local.connection

    def close(self) -> None:
        """Close the database connection for the current thread."""
        if hasattr(self._local, "connection") and self._local.connection is not None:
            self._local.connection.close()
            self._local.connection = None
