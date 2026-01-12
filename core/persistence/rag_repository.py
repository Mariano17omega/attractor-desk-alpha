"""RAG repository implementation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional
import uuid

from .database import Database


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
    ) -> RagDocument:
        document_id = str(uuid.uuid4())
        now = datetime.now()
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
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                workspace_id,
                artifact_entry_id,
                source_type,
                source_name,
                source_path,
                content_hash,
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
                updated_at = ?
            WHERE id = ?
            """,
            (
                source_name,
                source_path,
                artifact_entry_id,
                content_hash,
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
                   content_hash, created_at, updated_at
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
                   content_hash, created_at, updated_at
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
                (session_id, query, limit),
            )
        else:
            if not workspace_id:
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
                (workspace_id, query, limit),
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
            if not workspace_id:
                return []
            cursor = conn.execute(
                """
                SELECT e.chunk_id, e.embedding_blob, e.dims
                FROM rag_embeddings e
                JOIN rag_chunks c ON c.id = e.chunk_id
                JOIN rag_documents d ON d.id = c.document_id
                WHERE d.workspace_id = ? AND e.model = ?
                """,
                (workspace_id, model),
            )
        return [
            (row["chunk_id"], row["embedding_blob"], row["dims"])
            for row in cursor.fetchall()
        ]


def _row_to_document(row: dict) -> RagDocument:
    return RagDocument(
        id=row["id"],
        workspace_id=row["workspace_id"],
        artifact_entry_id=row["artifact_entry_id"],
        source_type=row["source_type"],
        source_name=row["source_name"],
        source_path=row["source_path"],
        content_hash=row["content_hash"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


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
