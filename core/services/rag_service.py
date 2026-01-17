"""RAG indexing and retrieval service."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import logging
import math
from typing import Optional
import uuid

from PySide6.QtCore import QObject, QThread, Signal

from core.llm.embeddings import OpenRouterEmbeddings
from core.llm.openrouter import get_chat_model
from core.persistence.rag_repository import (
    RagChunkDetails,
    RagChunkInput,
    RagEmbeddingInput,
    RagRepository,
)
from core.utils.chunking import chunk_markdown

logger = logging.getLogger(__name__)

EMBEDDING_STATUS_DISABLED = "disabled"
EMBEDDING_STATUS_INDEXED = "indexed"
EMBEDDING_STATUS_FAILED = "failed"
EMBEDDING_STATUS_SKIPPED = "skipped"


@dataclass(frozen=True)
class RagIndexRequest:
    """Payload describing an artifact to index."""

    workspace_id: str
    session_id: Optional[str]
    artifact_entry_id: Optional[str]
    source_type: str
    source_name: str
    content: str
    source_path: Optional[str] = None
    file_size: Optional[int] = None
    chunk_size_chars: int = 1200
    chunk_overlap_chars: int = 150
    embedding_model: Optional[str] = None
    embeddings_enabled: bool = False
    api_key: Optional[str] = None


@dataclass(frozen=True)
class RagIndexResult:
    """Result of an indexing run."""

    success: bool
    document_id: Optional[str]
    chunk_count: int
    skipped: bool = False
    embedding_status: str = EMBEDDING_STATUS_DISABLED
    embedding_error: str = ""
    error_message: str = ""


@dataclass(frozen=True)
class RagRetrievalSettings:
    """Runtime settings for retrieval and rerank."""

    scope: str = "session"
    k_lex: int = 8
    k_vec: int = 8
    rrf_k: int = 60
    max_candidates: int = 12
    max_context_chunks: int = 6
    max_context_chars: int = 6000
    enable_llm_rerank: bool = False


@dataclass(frozen=True)
class RagRetrievalResult:
    """Result of a retrieval run."""

    context: str
    citations: list[dict]
    candidates: list[dict]
    grounded: bool
    selected_chunk_ids: list[str]
    debug: dict


class _IndexWorker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def __init__(
        self,
        repository: RagRepository,
        request: RagIndexRequest,
        chroma_service: Optional["ChromaService"] = None,
    ):
        super().__init__()
        self._repository = repository
        self._request = request
        self._chroma_service = chroma_service

    def run(self) -> None:
        try:
            result = _index_document(self._repository, self._request, self._chroma_service)
            self.finished.emit(result)
        except Exception as exc:
            logger.exception("RAG indexing failed")
            self.error.emit(str(exc))
        finally:
            # Explicitly close thread-local database connections
            # This prevents connection leaks when worker threads terminate
            from core.persistence import Database
            db = Database()
            db.close()


class RagService(QObject):
    """Service for indexing artifacts into local RAG storage."""

    index_complete = Signal(object)
    index_error = Signal(str)

    def __init__(
        self,
        repository: RagRepository,
        chroma_service: Optional["ChromaService"] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._repository = repository
        self._chroma_service = chroma_service
        self._thread: Optional[QThread] = None
        self._worker: Optional[_IndexWorker] = None

    def index_artifact(self, request: RagIndexRequest) -> None:
        if self.is_busy():
            self.index_error.emit("RAG indexing already in progress")
            return
        self._thread = QThread()
        self._worker = _IndexWorker(self._repository, request, self._chroma_service)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._on_worker_error)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup)
        self._thread.start()

    def is_busy(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def _on_worker_finished(self, result: RagIndexResult) -> None:
        self.index_complete.emit(result)

    def _on_worker_error(self, error: str) -> None:
        self.index_error.emit(error)

    def _cleanup(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
        if self._thread is not None:
            self._thread.deleteLater()
            self._thread = None

    def retrieve(
        self,
        query: str,
        settings: RagRetrievalSettings,
        workspace_id: Optional[str],
        session_id: Optional[str],
        embedding_model: Optional[str],
        api_key: Optional[str] = None,
        queries: Optional[list[str]] = None,
    ) -> RagRetrievalResult:
        query_list = queries or [query]
        lexical_lists: list[list[str]] = []
        vector_lists: list[list[str]] = []
        lexical_scores: dict[str, float] = {}
        vector_scores: dict[str, float] = {}

        for q in query_list:
            lexical = self._repository.search_lexical(
                query=q,
                scope=settings.scope,
                workspace_id=workspace_id,
                session_id=session_id,
                limit=settings.k_lex,
            )
            lexical_lists.append([chunk_id for chunk_id, _score in lexical])
            for chunk_id, score in lexical:
                lexical_scores[chunk_id] = min(score, lexical_scores.get(chunk_id, score))

            if embedding_model:
                vector = self._vector_search(
                    query=q,
                    scope=settings.scope,
                    workspace_id=workspace_id,
                    session_id=session_id,
                    model=embedding_model,
                    k_vec=settings.k_vec,
                    api_key=api_key,
                )
                vector_lists.append([chunk_id for chunk_id, _score in vector])
                for chunk_id, score in vector:
                    vector_scores[chunk_id] = max(score, vector_scores.get(chunk_id, score))

        fused = _rrf_fuse(lexical_lists + vector_lists, settings.rrf_k)
        fused_sorted = sorted(fused.items(), key=lambda item: item[1], reverse=True)
        candidate_ids = [chunk_id for chunk_id, _score in fused_sorted[:settings.max_candidates]]

        chunk_details = self._repository.get_chunk_details(candidate_ids)
        details_by_id = {chunk.id: chunk for chunk in chunk_details}
        candidates = [
            _candidate_dict(
                chunk_id=chunk_id,
                fused_score=fused.get(chunk_id, 0.0),
                lexical_score=lexical_scores.get(chunk_id),
                vector_score=vector_scores.get(chunk_id),
                details=details_by_id.get(chunk_id),
            )
            for chunk_id in candidate_ids
        ]

        reranked = self._rerank_candidates(
            query=query,
            candidates=candidates,
            details_by_id=details_by_id,
            settings=settings,
            api_key=api_key,
        )
        context_chunks = _select_context_chunks(
            reranked,
            details_by_id=details_by_id,
            max_chunks=settings.max_context_chunks,
            max_chars=settings.max_context_chars,
        )
        context, citations = _build_context(context_chunks, details_by_id)
        grounded = bool(context_chunks)

        debug = {
            "lexical_candidates": len(lexical_scores),
            "vector_candidates": len(vector_scores),
            "fused_candidates": len(fused),
            "selected_candidates": len(candidate_ids),
            "context_chunks": len(context_chunks),
        }

        return RagRetrievalResult(
            context=context,
            citations=citations,
            candidates=reranked,
            grounded=grounded,
            selected_chunk_ids=context_chunks,
            debug=debug,
        )

    def _vector_search(
        self,
        query: str,
        scope: str,
        workspace_id: Optional[str],
        session_id: Optional[str],
        model: str,
        k_vec: int,
        api_key: Optional[str],
    ) -> list[tuple[str, float]]:
        """Perform vector similarity search using ChromaDB or fallback to manual search.

        If ChromaService is available, uses fast HNSW-based search.
        Otherwise, falls back to manual O(n) cosine similarity computation.
        """
        # Generate query embedding
        embedder = OpenRouterEmbeddings(model=model, api_key=api_key)
        query_vector = embedder.embed_text(query)
        if not query_vector:
            return []

        # Try ChromaDB first (100x+ faster for large collections)
        if self._chroma_service is not None:
            try:
                # Build metadata filter for scope
                # Note: ChromaDB doesn't support None in metadata, use empty string for Global RAG
                where_filter = {"workspace_id": workspace_id}
                if scope == "session" and session_id:
                    where_filter["session_id"] = session_id
                else:
                    # Global RAG: session_id is stored as empty string
                    where_filter["session_id"] = ""

                results = self._chroma_service.query_similar(
                    query_vector=query_vector,
                    where=where_filter,
                    k=k_vec,
                )
                return results
            except Exception as exc:
                logger.warning(f"ChromaDB query failed, falling back to manual search: {exc}")

        # Fallback: Manual O(n) search (slow for large collections)
        embeddings = self._repository.get_embeddings_for_scope(
            scope=scope,
            workspace_id=workspace_id,
            session_id=session_id,
            model=model,
        )
        if not embeddings:
            return []

        query_norm = _vector_norm(query_vector)
        if query_norm == 0:
            return []

        scored: list[tuple[str, float]] = []
        for chunk_id, blob, dims in embeddings:
            vector = _blob_to_float_list(blob)
            if dims and len(vector) != dims:
                continue
            score = _cosine_similarity(query_vector, vector, query_norm)
            scored.append((chunk_id, score))

        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:k_vec]

    def _rerank_candidates(
        self,
        query: str,
        candidates: list[dict],
        details_by_id: dict[str, RagChunkDetails],
        settings: RagRetrievalSettings,
        api_key: Optional[str],
    ) -> list[dict]:
        if not candidates:
            return []
        if settings.enable_llm_rerank:
            reranked = _llm_rerank(
                query=query,
                candidates=candidates,
                details_by_id=details_by_id,
                api_key=api_key,
            )
            if reranked:
                return reranked
        return _heuristic_rerank(candidates, details_by_id, settings.scope)


def _embeddings_requested(request: RagIndexRequest) -> bool:
    return bool(request.embeddings_enabled and request.embedding_model)


def _needs_embedding_retry(document, request: RagIndexRequest) -> bool:
    if not _embeddings_requested(request):
        return False
    if document.embedding_status != EMBEDDING_STATUS_INDEXED:
        return True
    return document.embedding_model != request.embedding_model


def _index_document(
    repository: RagRepository,
    request: RagIndexRequest,
    chroma_service: Optional["ChromaService"] = None,
    embedding_cache: Optional[dict[tuple[str, str, int, int], list[list[float]]]] = None,
) -> RagIndexResult:
    content_hash = _hash_content(request.content)
    document = None
    if request.artifact_entry_id:
        document = repository.get_document_by_artifact_entry(
            request.workspace_id,
            request.artifact_entry_id,
        )
    if document and document.content_hash == content_hash:
        if request.session_id:
            repository.attach_document_to_session(document.id, request.session_id)
        if not _needs_embedding_retry(document, request):
            return RagIndexResult(
                success=True,
                document_id=document.id,
                chunk_count=0,
                skipped=True,
                embedding_status=document.embedding_status,
                embedding_error=document.embedding_error or "",
            )

    if document is None:
        document = repository.create_document(
            workspace_id=request.workspace_id,
            source_type=request.source_type,
            source_name=request.source_name,
            content_hash=content_hash,
            artifact_entry_id=request.artifact_entry_id,
            source_path=request.source_path,
            file_size=request.file_size,
        )
    else:
        repository.update_document(
            document_id=document.id,
            source_name=request.source_name,
            content_hash=content_hash,
            source_path=request.source_path,
            artifact_entry_id=request.artifact_entry_id,
            file_size=request.file_size,
        )

    chunks = chunk_markdown(
        request.content,
        chunk_size_chars=request.chunk_size_chars,
        chunk_overlap_chars=request.chunk_overlap_chars,
    )
    chunk_inputs = [
        RagChunkInput(
            id=str(uuid.uuid4()),
            chunk_index=index,
            content=chunk.text,
            section_title=chunk.section_title,
            token_count=None,
        )
        for index, chunk in enumerate(chunks)
    ]
    repository.replace_document_chunks(document.id, chunk_inputs, request.source_name)

    if request.session_id:
        repository.attach_document_to_session(document.id, request.session_id)

    embedding_status = EMBEDDING_STATUS_DISABLED
    embedding_error = ""
    embedding_model = None
    if _embeddings_requested(request):
        embedding_model = request.embedding_model
        if not chunk_inputs:
            embedding_status = EMBEDDING_STATUS_SKIPPED
        else:
            try:
                cache_key = None
                vectors: Optional[list[list[float]]] = None
                if embedding_cache is not None:
                    cache_key = (
                        content_hash,
                        request.embedding_model,
                        request.chunk_size_chars,
                        request.chunk_overlap_chars,
                    )
                    cached = embedding_cache.get(cache_key)
                    if cached is not None and len(cached) == len(chunk_inputs):
                        vectors = cached
                if vectors is None:
                    embedder = OpenRouterEmbeddings(
                        model=request.embedding_model,
                        api_key=request.api_key,
                    )
                    unique_texts: list[str] = []
                    unique_index: dict[str, int] = {}
                    for chunk in chunk_inputs:
                        if chunk.content not in unique_index:
                            unique_index[chunk.content] = len(unique_texts)
                            unique_texts.append(chunk.content)
                    unique_vectors = embedder.embed_texts(unique_texts)
                    if len(unique_vectors) != len(unique_texts):
                        raise ValueError("Embedding count mismatch")
                    vectors = [unique_vectors[unique_index[chunk.content]] for chunk in chunk_inputs]
                    if cache_key is not None:
                        embedding_cache[cache_key] = vectors
                embeddings = [
                    RagEmbeddingInput(
                        chunk_id=chunk.id,
                        model=request.embedding_model,
                        dims=len(vector),
                        embedding_blob=_float_list_to_blob(vector),
                    )
                    for chunk, vector in zip(chunk_inputs, vectors)
                ]
                if len(embeddings) != len(chunk_inputs):
                    raise ValueError("Embedding count mismatch")
                repository.upsert_embeddings(embeddings)

                # Also add to ChromaDB for fast retrieval (if available)
                if chroma_service is not None:
                    try:
                        chunk_metadata = [
                            {
                                "chunk_id": chunk.id,
                                "document_id": document.id,
                                "workspace_id": request.workspace_id,
                                "session_id": request.session_id or "",  # ChromaDB doesn't support None in metadata
                            }
                            for chunk in chunk_inputs
                        ]
                        chroma_service.add_embeddings(
                            chunk_ids=[c.id for c in chunk_inputs],
                            vectors=vectors,
                            metadata=chunk_metadata,
                        )
                        logger.debug(f"Added {len(chunk_inputs)} vectors to ChromaDB for document {document.id}")
                    except Exception as exc:
                        logger.warning(f"Failed to add embeddings to ChromaDB (non-fatal): {exc}")

                embedding_status = EMBEDDING_STATUS_INDEXED
            except Exception as exc:
                embedding_status = EMBEDDING_STATUS_FAILED
                embedding_error = str(exc)
                logger.warning(
                    "Embedding generation failed for document %s: %s",
                    document.id,
                    exc,
                )

    repository.update_document_embedding_status(
        document_id=document.id,
        embedding_status=embedding_status,
        embedding_model=embedding_model,
        embedding_error=embedding_error or None,
    )

    return RagIndexResult(
        success=True,
        document_id=document.id,
        chunk_count=len(chunk_inputs),
        embedding_status=embedding_status,
        embedding_error=embedding_error,
    )


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _float_list_to_blob(values: list[float]) -> bytes:
    import array

    return array.array("f", values).tobytes()


def _blob_to_float_list(blob: bytes) -> list[float]:
    import array

    floats = array.array("f")
    floats.frombytes(blob)
    return list(floats)


def _vector_norm(values: list[float]) -> float:
    return math.sqrt(sum(value * value for value in values))


def _cosine_similarity(query: list[float], vector: list[float], query_norm: float) -> float:
    if not vector:
        return 0.0
    vector_norm = _vector_norm(vector)
    if vector_norm == 0 or query_norm == 0:
        return 0.0
    dot = sum(a * b for a, b in zip(query, vector))
    return dot / (query_norm * vector_norm)


def _rrf_fuse(rank_lists: list[list[str]], rrf_k: int) -> dict[str, float]:
    scores: dict[str, float] = {}
    for rank_list in rank_lists:
        for rank, chunk_id in enumerate(rank_list, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
    return scores


def _candidate_dict(
    chunk_id: str,
    fused_score: float,
    lexical_score: Optional[float],
    vector_score: Optional[float],
    details: Optional[RagChunkDetails],
) -> dict:
    data = {
        "chunk_id": chunk_id,
        "fused_score": fused_score,
        "lexical_score": lexical_score,
        "vector_score": vector_score,
    }
    if details:
        data.update(
            {
                "document_id": details.document_id,
                "chunk_index": details.chunk_index,
                "section_title": details.section_title,
                "source_name": details.source_name,
                "source_type": details.source_type,
            }
        )
    return data


def _heuristic_rerank(
    candidates: list[dict],
    details_by_id: dict[str, RagChunkDetails],
    scope: str,
) -> list[dict]:
    candidates = sorted(candidates, key=lambda item: item.get("fused_score", 0.0), reverse=True)
    doc_counts: dict[str, int] = {}
    updated_times = [
        details.document_updated_at.timestamp()
        for details in details_by_id.values()
    ]
    min_updated = min(updated_times) if updated_times else 0.0
    max_updated = max(updated_times) if updated_times else 0.0
    reranked: list[dict] = []
    for candidate in candidates:
        chunk_id = candidate["chunk_id"]
        details = details_by_id.get(chunk_id)
        if not details:
            reranked.append(candidate)
            continue
        doc_seen = doc_counts.get(details.document_id, 0)
        doc_counts[details.document_id] = doc_seen + 1

        score = candidate.get("fused_score", 0.0)
        if details.section_title:
            score += 0.05
        if doc_seen:
            score *= 0.9 ** doc_seen
        if scope == "session" and max_updated > min_updated:
            recency = (details.document_updated_at.timestamp() - min_updated) / (
                max_updated - min_updated
            )
            score += recency * 0.03
        reranked.append({**candidate, "rerank_score": score})
    reranked.sort(key=lambda item: item.get("rerank_score", 0.0), reverse=True)
    return reranked


def _llm_rerank(
    query: str,
    candidates: list[dict],
    details_by_id: dict[str, RagChunkDetails],
    api_key: Optional[str],
) -> list[dict]:
    if not candidates:
        return []
    prompt_lines = [
        "You are reranking retrieved passages for relevance to the user query.",
        "Return a JSON array of candidate indices (1-based) ordered from best to worst.",
        "Do not include any extra text.",
        "",
        f"Query: {query}",
        "",
        "Candidates:",
    ]
    for idx, candidate in enumerate(candidates, start=1):
        details = details_by_id.get(candidate["chunk_id"])
        source = details.source_name if details else "unknown"
        section = details.section_title if details and details.section_title else "n/a"
        text = details.content if details else ""
        prompt_lines.append(f"[{idx}] {source} | {section}\n{text}")
    prompt = "\n".join(prompt_lines)

    model = get_chat_model(
        model="anthropic/claude-3.5-sonnet",
        temperature=0.0,
        streaming=False,
        api_key=api_key,
    )
    response = model.invoke(
        [
            {"role": "system", "content": "You output strict JSON arrays only."},
            {"role": "user", "content": prompt},
        ]
    )
    try:
        import json

        order = json.loads(response.content)
    except Exception:
        return []
    if not isinstance(order, list):
        return []
    reordered: list[dict] = []
    for item in order:
        if not isinstance(item, int):
            continue
        index = item - 1
        if 0 <= index < len(candidates):
            reordered.append(candidates[index])
    return reordered if reordered else []


def _select_context_chunks(
    candidates: list[dict],
    details_by_id: dict[str, RagChunkDetails],
    max_chunks: int,
    max_chars: int,
) -> list[str]:
    selected: list[str] = []
    selected_map: dict[str, set[int]] = {}
    total_chars = 0
    for candidate in candidates:
        chunk_id = candidate["chunk_id"]
        details = details_by_id.get(chunk_id)
        if not details:
            continue
        doc_set = selected_map.setdefault(details.document_id, set())
        if details.chunk_index in doc_set or any(
            abs(details.chunk_index - idx) <= 1 for idx in doc_set
        ):
            continue
        chunk_len = len(details.content)
        if total_chars + chunk_len > max_chars and selected:
            break
        selected.append(chunk_id)
        doc_set.add(details.chunk_index)
        total_chars += chunk_len
        if len(selected) >= max_chunks:
            break
    return selected


def _build_context(
    chunk_ids: list[str],
    details_by_id: dict[str, RagChunkDetails],
) -> tuple[str, list[dict]]:
    if not chunk_ids:
        return "", []
    lines = ["<retrieved-context>"]
    citations: list[dict] = []
    for idx, chunk_id in enumerate(chunk_ids, start=1):
        details = details_by_id.get(chunk_id)
        if not details:
            continue
        header = details.source_name
        if details.section_title:
            header = f"{header} | {details.section_title}"
        lines.append(f"[{idx}] {header}")
        lines.append(details.content)
        lines.append("")
        citations.append(
            {
                "chunk_id": details.id,
                "document_id": details.document_id,
                "source_name": details.source_name,
                "section_title": details.section_title,
                "chunk_index": details.chunk_index,
            }
        )
    lines.append("</retrieved-context>")
    return "\n".join(lines).strip(), citations
