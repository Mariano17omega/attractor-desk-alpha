"""RAG repository implementation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Iterable, Optional
import uuid

from .database import Database

GLOBAL_WORKSPACE_ID = "GLOBAL"
_FTS_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


@dataclass(frozen=True)
class RagDocument:
    """Persisted RAG document metadata."""

    id: str
    workspace_id: str
    artifact_entry_id: Optional[str]
    source_type: str
    source_name: str
    source_path: Optional[str]
    content_hash: str
    indexed_at: Optional[datetime]
    file_size: Optional[int]
    embedding_status: str
    embedding_model: Optional[str]
    embedding_error: Optional[str]
    stale_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class RagChunk:
    """Persisted RAG chunk metadata."""

    id: str
    document_id: str
    chunk_index: int
    section_title: Optional[str]
    content: str
    token_count: Optional[int]
    created_at: datetime


@dataclass(frozen=True)
class RagChunkDetails:
    """Chunk metadata with document context."""

    id: str
    document_id: str
    chunk_index: int
    section_title: Optional[str]
    content: str
    token_count: Optional[int]
    created_at: datetime
    source_name: str
    source_type: str
    source_path: Optional[str]
    document_updated_at: datetime


@dataclass(frozen=True)
class RagChunkInput:
    """Chunk input payload used during indexing."""

    id: str
    chunk_index: int
    content: str
    section_title: Optional[str] = None
    token_count: Optional[int] = None


@dataclass(frozen=True)
class RagEmbeddingInput:
    """Embedding payload for a chunk."""

    chunk_id: str
    model: str
    dims: int
    embedding_blob: bytes


@dataclass(frozen=True)
class RagIndexRegistryEntry:
    """Registry entry for PDF indexing."""

    source_path: str
    content_hash: str
    status: str
    retry_count: int
    last_seen_at: Optional[datetime]
    last_indexed_at: Optional[datetime]
    error_message: Optional[str]
    embedding_model: Optional[str]
    embedding_status: Optional[str]
    embedding_error: Optional[str]


class RagRepository:
    """Repository for RAG persistence operations."""

    def __init__(self, database: Database):
        self._db = database

    def create_document(
        self,
        workspace_id: str,
        source_type: str,
        source_name: str,
        content_hash: str,
        artifact_entry_id: Optional[str] = None,
        source_path: Optional[str] = None,
        file_size: Optional[int] = None,
        embedding_status: str = "disabled",
        embedding_model: Optional[str] = None,
        embedding_error: Optional[str] = None,
        indexed_at: Optional[datetime] = None,
        stale_at: Optional[datetime] = None,
    ) -> RagDocument:
        document_id = str(uuid.uuid4())
        now = datetime.now()
        indexed_at_value = indexed_at or now
        stale_at_value = stale_at.isoformat() if stale_at else None
        conn = self._db.get_connection()
        conn.execute(
            """
            INSERT INTO rag_documents (
                id,
                workspace_id,
                artifact_entry_id,
                source_type,
                source_name,
                source_path,
                content_hash,
                indexed_at,
                file_size,
                embedding_status,
                embedding_model,
                embedding_error,
                stale_at,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                workspace_id,
                artifact_entry_id,
                source_type,
                source_name,
                source_path,
                content_hash,
                indexed_at_value.isoformat(),
                file_size,
                embedding_status,
                embedding_model,
                embedding_error,
                stale_at_value,
                now.isoformat(),
                now.isoformat(),
            ),
        )
        conn.commit()
        return RagDocument(
            id=document_id,
            workspace_id=workspace_id,
            artifact_entry_id=artifact_entry_id,
            source_type=source_type,
            source_name=source_name,
            source_path=source_path,
            content_hash=content_hash,
            indexed_at=indexed_at_value,
            file_size=file_size,
            embedding_status=embedding_status,
            embedding_model=embedding_model,
            embedding_error=embedding_error,
            stale_at=stale_at,
            created_at=now,
            updated_at=now,
        )

    def update_document(
        self,
        document_id: str,
        source_name: str,
        content_hash: str,
        source_path: Optional[str] = None,
        artifact_entry_id: Optional[str] = None,
        file_size: Optional[int] = None,
    ) -> None:
        conn = self._db.get_connection()
        now = datetime.now().isoformat()
        conn.execute(
            """
            UPDATE rag_documents
            SET source_name = ?,
                source_path = ?,
                artifact_entry_id = ?,
                content_hash = ?,
                indexed_at = ?,
                file_size = COALESCE(?, file_size),
                updated_at = ?
            WHERE id = ?
            """,
            (
                source_name,
                source_path,
                artifact_entry_id,
                content_hash,
                now,
                file_size,
                now,
                document_id,
            ),
        )
        conn.commit()

    def update_document_embedding_status(
        self,
        document_id: str,
        embedding_status: str,
        embedding_model: Optional[str] = None,
        embedding_error: Optional[str] = None,
    ) -> None:
        conn = self._db.get_connection()
        now = datetime.now().isoformat()
        conn.execute(
            """
            UPDATE rag_documents
            SET embedding_status = ?,
                embedding_model = ?,
                embedding_error = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                embedding_status,
                embedding_model,
                embedding_error,
                now,
                document_id,
            ),
        )
        conn.commit()

    def get_document(self, document_id: str) -> Optional[RagDocument]:
        conn = self._db.get_connection()
        cursor = conn.execute(
            """
            SELECT id, workspace_id, artifact_entry_id, source_type, source_name, source_path,
                   content_hash, indexed_at, file_size, embedding_status, embedding_model,
                   embedding_error, stale_at, created_at, updated_at
            FROM rag_documents
            WHERE id = ?
            """,
            (document_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return _row_to_document(row)

    def get_document_by_artifact_entry(
        self,
        workspace_id: str,
        artifact_entry_id: str,
    ) -> Optional[RagDocument]:
        conn = self._db.get_connection()
        cursor = conn.execute(
            """
            SELECT id, workspace_id, artifact_entry_id, source_type, source_name, source_path,
                   content_hash, indexed_at, file_size, embedding_status, embedding_model,
                   embedding_error, stale_at, created_at, updated_at
            FROM rag_documents
            WHERE workspace_id = ? AND artifact_entry_id = ?
            """,
            (workspace_id, artifact_entry_id),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return _row_to_document(row)

    def delete_document(self, document_id: str) -> None:
        conn = self._db.get_connection()
        conn.execute(
            """
            DELETE FROM rag_chunks_fts
            WHERE chunk_id IN (
                SELECT id FROM rag_chunks WHERE document_id = ?
            )
            """,
            (document_id,),
        )
        conn.execute("DELETE FROM rag_documents WHERE id = ?", (document_id,))
        conn.commit()

    def mark_session_documents_stale(self, session_id: str, stale_at: datetime) -> None:
        conn = self._db.get_connection()
        conn.execute(
            """
            UPDATE rag_documents
            SET stale_at = ?
            WHERE id IN (
                SELECT document_id FROM rag_document_sessions WHERE session_id = ?
            ) AND source_type = 'chatpdf'
            """,
            (stale_at.isoformat(), session_id),
        )
        conn.commit()

    def list_stale_documents(self, cutoff: datetime) -> list[RagDocument]:
        conn = self._db.get_connection()
        cursor = conn.execute(
            """
            SELECT id, workspace_id, artifact_entry_id, source_type, source_name, source_path,
                   content_hash, indexed_at, file_size, embedding_status, embedding_model,
                   embedding_error, stale_at, created_at, updated_at
            FROM rag_documents
            WHERE stale_at IS NOT NULL AND stale_at <= ? AND source_type = 'chatpdf'
            ORDER BY stale_at ASC
            """,
            (cutoff.isoformat(),),
        )
        return [_row_to_document(row) for row in cursor.fetchall()]

    def attach_document_to_session(self, document_id: str, session_id: str) -> None:
        conn = self._db.get_connection()
        now = datetime.now().isoformat()
        conn.execute(
            """
            INSERT OR IGNORE INTO rag_document_sessions (document_id, session_id, created_at)
            VALUES (?, ?, ?)
            """,
            (document_id, session_id, now),
        )
        conn.commit()

    def detach_document_from_session(self, document_id: str, session_id: str) -> None:
        conn = self._db.get_connection()
        conn.execute(
            """
            DELETE FROM rag_document_sessions
            WHERE document_id = ? AND session_id = ?
            """,
            (document_id, session_id),
        )
        conn.commit()

    def replace_document_chunks(
        self,
        document_id: str,
        chunks: Iterable[RagChunkInput],
        source_name: str,
    ) -> None:
        conn = self._db.get_connection()
        now = datetime.now().isoformat()
        conn.execute(
            """
            DELETE FROM rag_chunks_fts
            WHERE chunk_id IN (
                SELECT id FROM rag_chunks WHERE document_id = ?
            )
            """,
            (document_id,),
        )
        conn.execute("DELETE FROM rag_chunks WHERE document_id = ?", (document_id,))
        chunk_rows = []
        fts_rows = []
        for chunk in chunks:
            chunk_rows.append(
                (
                    chunk.id,
                    document_id,
                    chunk.chunk_index,
                    chunk.section_title,
                    chunk.content,
                    chunk.token_count,
                    now,
                )
            )
            fts_rows.append((chunk.id, chunk.content, chunk.section_title, source_name))
        if chunk_rows:
            conn.executemany(
                """
                INSERT INTO rag_chunks (
                    id,
                    document_id,
                    chunk_index,
                    section_title,
                    content,
                    token_count,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                chunk_rows,
            )
            conn.executemany(
                """
                INSERT INTO rag_chunks_fts (chunk_id, content, section_title, source_name)
                VALUES (?, ?, ?, ?)
                """,
                fts_rows,
            )
        conn.commit()

    def get_chunks_by_ids(self, chunk_ids: Iterable[str]) -> list[RagChunk]:
        chunk_ids = list(chunk_ids)
        if not chunk_ids:
            return []
        conn = self._db.get_connection()
        placeholders = ",".join(["?"] * len(chunk_ids))
        cursor = conn.execute(
            f"""
            SELECT id, document_id, chunk_index, section_title, content, token_count, created_at
            FROM rag_chunks
            WHERE id IN ({placeholders})
            """,
            tuple(chunk_ids),
        )
        return [_row_to_chunk(row) for row in cursor.fetchall()]

    def get_chunk_details(self, chunk_ids: Iterable[str]) -> list[RagChunkDetails]:
        chunk_ids = list(chunk_ids)
        if not chunk_ids:
            return []
        conn = self._db.get_connection()
        placeholders = ",".join(["?"] * len(chunk_ids))
        cursor = conn.execute(
            f"""
            SELECT
                c.id,
                c.document_id,
                c.chunk_index,
                c.section_title,
                c.content,
                c.token_count,
                c.created_at,
                d.source_name,
                d.source_type,
                d.source_path,
                d.updated_at
            FROM rag_chunks c
            JOIN rag_documents d ON d.id = c.document_id
            WHERE c.id IN ({placeholders})
            """,
            tuple(chunk_ids),
        )
        return [_row_to_chunk_details(row) for row in cursor.fetchall()]

    def upsert_embeddings(self, embeddings: Iterable[RagEmbeddingInput]) -> None:
        embeddings = list(embeddings)
        if not embeddings:
            return
        conn = self._db.get_connection()
        now = datetime.now().isoformat()
        conn.executemany(
            """
            INSERT INTO rag_embeddings (chunk_id, model, dims, embedding_blob, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(chunk_id) DO UPDATE SET
                model = excluded.model,
                dims = excluded.dims,
                embedding_blob = excluded.embedding_blob,
                created_at = excluded.created_at
            """,
            [
                (
                    embedding.chunk_id,
                    embedding.model,
                    embedding.dims,
                    embedding.embedding_blob,
                    now,
                )
                for embedding in embeddings
            ],
        )
        conn.commit()

    def search_lexical(
        self,
        query: str,
        scope: str,
        workspace_id: Optional[str],
        session_id: Optional[str],
        limit: int,
    ) -> list[tuple[str, float]]:
        if not query:
            return []
        safe_query = _escape_fts5_query(query)
        if not safe_query:
            return []
        conn = self._db.get_connection()
        if scope == "session":
            if not session_id:
                return []
            cursor = conn.execute(
                """
                SELECT rag_chunks_fts.chunk_id, bm25(rag_chunks_fts) AS score
                FROM rag_chunks_fts
                JOIN rag_chunks c ON c.id = rag_chunks_fts.chunk_id
                JOIN rag_documents d ON d.id = c.document_id
                JOIN rag_document_sessions s ON s.document_id = d.id
                WHERE s.session_id = ? AND rag_chunks_fts MATCH ?
                ORDER BY score
                LIMIT ?
                """,
                (session_id, safe_query, limit),
            )
        else:
            workspace_scope = GLOBAL_WORKSPACE_ID if scope == "global" else workspace_id
            if not workspace_scope:
                return []
            cursor = conn.execute(
                """
                SELECT rag_chunks_fts.chunk_id, bm25(rag_chunks_fts) AS score
                FROM rag_chunks_fts
                JOIN rag_chunks c ON c.id = rag_chunks_fts.chunk_id
                JOIN rag_documents d ON d.id = c.document_id
                WHERE d.workspace_id = ? AND rag_chunks_fts MATCH ?
                ORDER BY score
                LIMIT ?
                """,
                (workspace_scope, safe_query, limit),
            )
        return [(row["chunk_id"], float(row["score"])) for row in cursor.fetchall()]

    def get_embeddings_for_scope(
        self,
        scope: str,
        workspace_id: Optional[str],
        session_id: Optional[str],
        model: str,
    ) -> list[tuple[str, bytes, int]]:
        conn = self._db.get_connection()
        if scope == "session":
            if not session_id:
                return []
            cursor = conn.execute(
                """
                SELECT e.chunk_id, e.embedding_blob, e.dims
                FROM rag_embeddings e
                JOIN rag_chunks c ON c.id = e.chunk_id
                JOIN rag_documents d ON d.id = c.document_id
                JOIN rag_document_sessions s ON s.document_id = d.id
                WHERE s.session_id = ? AND e.model = ?
                """,
                (session_id, model),
            )
        else:
            workspace_scope = GLOBAL_WORKSPACE_ID if scope == "global" else workspace_id
            if not workspace_scope:
                return []
            cursor = conn.execute(
                """
                SELECT e.chunk_id, e.embedding_blob, e.dims
                FROM rag_embeddings e
                JOIN rag_chunks c ON c.id = e.chunk_id
                JOIN rag_documents d ON d.id = c.document_id
                WHERE d.workspace_id = ? AND e.model = ?
                """,
                (workspace_scope, model),
            )
        return [
            (row["chunk_id"], row["embedding_blob"], row["dims"])
            for row in cursor.fetchall()
        ]

    def upsert_registry_entry(
        self,
        source_path: str,
        content_hash: str,
        status: str,
        retry_count: int = 0,
        last_seen_at: Optional[datetime] = None,
        last_indexed_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
        embedding_model: Optional[str] = None,
        embedding_status: Optional[str] = None,
        embedding_error: Optional[str] = None,
    ) -> None:
        conn = self._db.get_connection()
        conn.execute(
            """
            DELETE FROM rag_index_registry
            WHERE source_path = ? AND content_hash != ?
            """,
            (source_path, content_hash),
        )
        conn.execute(
            """
            INSERT INTO rag_index_registry (
                source_path,
                content_hash,
                status,
                retry_count,
                last_seen_at,
                last_indexed_at,
                error_message,
                embedding_model,
                embedding_status,
                embedding_error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_path, content_hash) DO UPDATE SET
                status = excluded.status,
                retry_count = excluded.retry_count,
                last_seen_at = excluded.last_seen_at,
                last_indexed_at = excluded.last_indexed_at,
                error_message = excluded.error_message,
                embedding_model = excluded.embedding_model,
                embedding_status = excluded.embedding_status,
                embedding_error = excluded.embedding_error
            """,
            (
                source_path,
                content_hash,
                status,
                retry_count,
                last_seen_at.isoformat() if last_seen_at else None,
                last_indexed_at.isoformat() if last_indexed_at else None,
                error_message,
                embedding_model,
                embedding_status,
                embedding_error,
            ),
        )
        conn.commit()

    def get_registry_entry(
        self, source_path: str, content_hash: str
    ) -> Optional[RagIndexRegistryEntry]:
        conn = self._db.get_connection()
        cursor = conn.execute(
            """
            SELECT source_path, content_hash, status, retry_count, last_seen_at, last_indexed_at,
                   error_message, embedding_model, embedding_status, embedding_error
            FROM rag_index_registry
            WHERE source_path = ? AND content_hash = ?
            """,
            (source_path, content_hash),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return _row_to_registry_entry(row)

    def list_registry_entries(
        self, status: Optional[str] = None
    ) -> list[RagIndexRegistryEntry]:
        conn = self._db.get_connection()
        if status:
            cursor = conn.execute(
                """
                SELECT source_path, content_hash, status, retry_count, last_seen_at, last_indexed_at,
                       error_message, embedding_model, embedding_status, embedding_error
                FROM rag_index_registry
                WHERE status = ?
                ORDER BY last_seen_at DESC
                """,
                (status,),
            )
        else:
            cursor = conn.execute(
                """
                SELECT source_path, content_hash, status, retry_count, last_seen_at, last_indexed_at,
                       error_message, embedding_model, embedding_status, embedding_error
                FROM rag_index_registry
                ORDER BY last_seen_at DESC
                """
            )
        return [_row_to_registry_entry(row) for row in cursor.fetchall()]

    def get_registry_status_counts(self) -> dict[str, int]:
        conn = self._db.get_connection()
        cursor = conn.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM rag_index_registry
            GROUP BY status
            """
        )
        return {row["status"]: int(row["count"]) for row in cursor.fetchall()}


def _row_to_document(row: dict) -> RagDocument:
    return RagDocument(
        id=row["id"],
        workspace_id=row["workspace_id"],
        artifact_entry_id=row["artifact_entry_id"],
        source_type=row["source_type"],
        source_name=row["source_name"],
        source_path=row["source_path"],
        content_hash=row["content_hash"],
        indexed_at=_parse_optional_datetime(row["indexed_at"]),
        file_size=row["file_size"],
        embedding_status=row["embedding_status"],
        embedding_model=row["embedding_model"],
        embedding_error=row["embedding_error"],
        stale_at=_parse_optional_datetime(row["stale_at"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _escape_fts5_query(query: str) -> str:
    tokens = _FTS_TOKEN_RE.findall(query)
    if not tokens:
        return ""
    return " ".join('"' + token.replace('"', '""') + '"' for token in tokens)


def _parse_optional_datetime(value: Optional[str]) -> Optional[datetime]:
    if value:
        return datetime.fromisoformat(value)
    return None


def _row_to_chunk(row: dict) -> RagChunk:
    return RagChunk(
        id=row["id"],
        document_id=row["document_id"],
        chunk_index=row["chunk_index"],
        section_title=row["section_title"],
        content=row["content"],
        token_count=row["token_count"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_chunk_details(row: dict) -> RagChunkDetails:
    return RagChunkDetails(
        id=row["id"],
        document_id=row["document_id"],
        chunk_index=row["chunk_index"],
        section_title=row["section_title"],
        content=row["content"],
        token_count=row["token_count"],
        created_at=datetime.fromisoformat(row["created_at"]),
        source_name=row["source_name"],
        source_type=row["source_type"],
        source_path=row["source_path"],
        document_updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _row_to_registry_entry(row: dict) -> RagIndexRegistryEntry:
    return RagIndexRegistryEntry(
        source_path=row["source_path"],
        content_hash=row["content_hash"],
        status=row["status"],
        retry_count=row["retry_count"],
        last_seen_at=_parse_optional_datetime(row["last_seen_at"]),
        last_indexed_at=_parse_optional_datetime(row["last_indexed_at"]),
        error_message=row["error_message"],
        embedding_model=row["embedding_model"],
        embedding_status=row["embedding_status"],
        embedding_error=row["embedding_error"],
    )
