"""ChromaDB service for fast vector similarity search.

This service provides a clean abstraction over ChromaDB for efficient
nearest-neighbor search, replacing the manual O(n) vector similarity
computation with HNSW-based approximate search.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ChromaService:
    """Service for managing ChromaDB collections and vector search.

    Uses a single collection with metadata filtering to support:
    - Global RAG (session_id=None)
    - ChatPDF RAG (session_id set)
    - Multi-tenant isolation via workspace_id
    """

    def __init__(self, persist_directory: Optional[str] = None):
        """Initialize ChromaDB client.

        Args:
            persist_directory: Path to ChromaDB storage. Defaults to ~/.attractor_desk/chromadb/
        """
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError:
            raise RuntimeError(
                "ChromaDB not installed. Run: pip install chromadb>=0.4.0"
            )

        if persist_directory is None:
            home = os.path.expanduser("~")
            persist_directory = os.path.join(home, ".attractor_desk", "chromadb")

        # Expand user paths and create directory
        persist_directory = os.path.expanduser(persist_directory)
        Path(persist_directory).mkdir(parents=True, exist_ok=True)

        logger.info(f"Initializing ChromaDB at {persist_directory}")

        self._client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=False,
            ),
        )

        # Use a single collection with metadata filtering for multi-tenancy
        self._collection = self._client.get_or_create_collection(
            name="rag_chunks",
            metadata={"hnsw:space": "cosine"},  # Use cosine distance
        )

        logger.info(f"ChromaDB collection 'rag_chunks' initialized with {self._collection.count()} vectors")

    def add_embeddings(
        self,
        chunk_ids: list[str],
        vectors: list[list[float]],
        metadata: list[dict],
    ) -> None:
        """Add or update embeddings in the collection.

        Args:
            chunk_ids: List of chunk IDs (must match SQLite chunk IDs)
            vectors: List of embedding vectors
            metadata: List of metadata dicts with:
                - chunk_id: str
                - document_id: str
                - workspace_id: str
                - session_id: Optional[str] (None for Global RAG)
        """
        if not chunk_ids:
            return

        if len(chunk_ids) != len(vectors) != len(metadata):
            raise ValueError("chunk_ids, vectors, and metadata must have same length")

        try:
            self._collection.upsert(
                ids=chunk_ids,
                embeddings=vectors,
                metadatas=metadata,
            )
            logger.debug(f"Added {len(chunk_ids)} embeddings to ChromaDB")
        except Exception as exc:
            logger.exception("Failed to add embeddings to ChromaDB")
            raise

    def query_similar(
        self,
        query_vector: list[float],
        where: dict,
        k: int = 10,
    ) -> list[tuple[str, float]]:
        """Query for similar vectors using metadata filtering.

        Args:
            query_vector: Query embedding vector
            where: Metadata filter dict (e.g., {"workspace_id": "...", "session_id": "..."})
                   For Global RAG, session_id should be "" (empty string, not None)
            k: Number of results to return

        Returns:
            List of (chunk_id, similarity_score) tuples, sorted by score descending
        """
        try:
            # ChromaDB requires explicit AND operator for multiple conditions
            # Convert dict to ChromaDB filter format
            if len(where) > 1:
                chroma_where = {
                    "$and": [
                        {key: value} for key, value in where.items()
                    ]
                }
            else:
                chroma_where = where

            results = self._collection.query(
                query_embeddings=[query_vector],
                where=chroma_where if chroma_where else None,
                n_results=k,
            )

            # ChromaDB returns cosine distance (lower is better)
            # Convert to similarity score (higher is better): similarity = 1 - distance
            chunk_ids = results["ids"][0] if results["ids"] else []
            distances = results["distances"][0] if results["distances"] else []

            # Convert distance to similarity score
            scored = [
                (chunk_id, 1.0 - distance)
                for chunk_id, distance in zip(chunk_ids, distances)
            ]

            return scored

        except Exception as exc:
            logger.exception("ChromaDB query failed")
            return []

    def delete_by_document(self, document_id: str) -> None:
        """Delete all chunks for a specific document.

        Args:
            document_id: Document ID to delete
        """
        try:
            self._collection.delete(
                where={"document_id": document_id}
            )
            logger.info(f"Deleted ChromaDB vectors for document {document_id}")
        except Exception as exc:
            logger.exception(f"Failed to delete document {document_id} from ChromaDB")

    def delete_by_session(self, session_id: str) -> None:
        """Delete all chunks for a specific session (ChatPDF cleanup).

        Args:
            session_id: Session ID to delete
        """
        try:
            self._collection.delete(
                where={"session_id": session_id}
            )
            logger.info(f"Deleted ChromaDB vectors for session {session_id}")
        except Exception as exc:
            logger.exception(f"Failed to delete session {session_id} from ChromaDB")

    def count(self) -> int:
        """Get total number of vectors in the collection."""
        return self._collection.count()

    def reset(self) -> None:
        """Delete all data in the collection. USE WITH CAUTION."""
        logger.warning("Resetting ChromaDB collection - all vectors will be deleted")
        self._client.delete_collection("rag_chunks")
        self._collection = self._client.get_or_create_collection(
            name="rag_chunks",
            metadata={"hnsw:space": "cosine"},
        )
