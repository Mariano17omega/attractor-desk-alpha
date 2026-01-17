"""Global RAG indexing service with registry tracking."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass
import hashlib
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from core.persistence.rag_repository import RagRepository
from core.services.docling_service import convert_pdf_to_markdown
from core.services.rag_service import (
    EMBEDDING_STATUS_INDEXED,
    RagIndexRequest,
    _index_document,
)

logger = logging.getLogger(__name__)

CONVERSION_BATCH_SIZE = 5
CONVERSION_TIMEOUT_SECONDS = 300


@dataclass(frozen=True)
class GlobalRagIndexRequest:
    """Payload describing a batch of PDFs to index globally."""

    workspace_id: str
    pdf_paths: list[str]
    chunk_size_chars: int = 1200
    chunk_overlap_chars: int = 150
    embedding_model: Optional[str] = None
    embeddings_enabled: bool = False
    api_key: Optional[str] = None
    force_reindex: bool = False


@dataclass(frozen=True)
class GlobalRagIndexResult:
    """Result summary for a global indexing run."""

    indexed: int
    skipped: int
    failed: int


class _GlobalIndexWorker(QObject):
    progress = Signal(int, int, str)
    finished = Signal(object)
    error = Signal(str)

    def __init__(
        self,
        repository: RagRepository,
        request: GlobalRagIndexRequest,
        chroma_service: Optional["ChromaService"] = None,
    ):
        super().__init__()
        self._repository = repository
        self._request = request
        self._chroma_service = chroma_service
        self._embedding_cache: dict[tuple[str, str, int, int], list[list[float]]] = {}
        self._markdown_cache: dict[str, str] = {}

    def run(self) -> None:
        try:
            result = self._run_index()
            self.finished.emit(result)
        except Exception as exc:
            logger.exception("Global RAG indexing failed")
            self.error.emit(str(exc))

    def _run_index(self) -> GlobalRagIndexResult:
        indexed = 0
        skipped = 0
        failed = 0
        pdf_paths = _sorted_paths_by_size(self._request.pdf_paths)
        total = len(pdf_paths)
        processed = 0
        to_convert: list[tuple[str, str, int, Optional[object]]] = []

        for pdf_path in pdf_paths:
            file_path = Path(pdf_path)
            if not file_path.exists() or not file_path.is_file():
                failed += 1
                processed += 1
                self._repository.upsert_registry_entry(
                    source_path=pdf_path,
                    content_hash="",
                    status="error",
                    retry_count=0,
                    last_seen_at=None,
                    last_indexed_at=None,
                    error_message="File not found",
                    embedding_model=self._request.embedding_model,
                    embedding_status=None,
                    embedding_error=None,
                )
                self.progress.emit(processed, total, pdf_path)
                continue

            file_size = file_path.stat().st_size
            file_hash = _hash_file(file_path)
            existing = self._repository.get_registry_entry(pdf_path, file_hash)
            embeddings_requested = bool(
                self._request.embeddings_enabled and self._request.embedding_model
            )
            embeddings_ready = True
            if embeddings_requested:
                embeddings_ready = (
                    existing is not None
                    and existing.embedding_status == EMBEDDING_STATUS_INDEXED
                    and existing.embedding_model == self._request.embedding_model
                )
            if (
                existing
                and existing.status == "indexed"
                and not self._request.force_reindex
                and embeddings_ready
            ):
                skipped += 1
                processed += 1
                self._repository.upsert_registry_entry(
                    source_path=pdf_path,
                    content_hash=file_hash,
                    status="indexed",
                    retry_count=existing.retry_count,
                    last_seen_at=_now(),
                    last_indexed_at=existing.last_indexed_at,
                    error_message=existing.error_message,
                    embedding_model=existing.embedding_model or self._request.embedding_model,
                    embedding_status=existing.embedding_status,
                    embedding_error=existing.embedding_error,
                )
                self.progress.emit(processed, total, pdf_path)
                continue

            self._repository.upsert_registry_entry(
                source_path=pdf_path,
                content_hash=file_hash,
                status="indexing",
                retry_count=existing.retry_count if existing else 0,
                last_seen_at=_now(),
                last_indexed_at=existing.last_indexed_at if existing else None,
                error_message=None,
                embedding_model=self._request.embedding_model,
                embedding_status=existing.embedding_status if existing else None,
                embedding_error=existing.embedding_error if existing else None,
            )

            cached_markdown = self._markdown_cache.get(file_hash)
            if cached_markdown is not None:
                if self._index_from_markdown(
                    pdf_path,
                    file_hash,
                    file_size,
                    cached_markdown,
                    file_path.stem,
                    existing,
                ):
                    indexed += 1
                else:
                    failed += 1
                processed += 1
                self.progress.emit(processed, total, pdf_path)
                continue

            to_convert.append((pdf_path, file_hash, file_size, existing))

        if to_convert:
            with ThreadPoolExecutor(max_workers=CONVERSION_BATCH_SIZE) as executor:
                for batch in _batch_items(to_convert, CONVERSION_BATCH_SIZE):
                    future_map = {
                        executor.submit(convert_pdf_to_markdown, item[0]): item
                        for item in batch
                    }
                    done, not_done = wait(
                        future_map,
                        timeout=CONVERSION_TIMEOUT_SECONDS,
                    )
                    for future in done:
                        pdf_path, file_hash, file_size, existing = future_map[future]
                        conversion = future.result()
                        if not conversion.success:
                            failed += 1
                            retry_count = (existing.retry_count + 1) if existing else 1
                            self._repository.upsert_registry_entry(
                                source_path=pdf_path,
                                content_hash=file_hash,
                                status="error",
                                retry_count=retry_count,
                                last_seen_at=_now(),
                                last_indexed_at=None,
                                error_message=conversion.error_message,
                                embedding_model=self._request.embedding_model,
                                embedding_status=None,
                                embedding_error=None,
                            )
                        else:
                            self._markdown_cache[file_hash] = conversion.markdown
                            if self._index_from_markdown(
                                pdf_path,
                                file_hash,
                                file_size,
                                conversion.markdown,
                                conversion.source_filename,
                                existing,
                            ):
                                indexed += 1
                            else:
                                failed += 1
                        processed += 1
                        self.progress.emit(processed, total, pdf_path)
                    for future in not_done:
                        pdf_path, file_hash, _file_size, existing = future_map[future]
                        future.cancel()
                        failed += 1
                        retry_count = (existing.retry_count + 1) if existing else 1
                        self._repository.upsert_registry_entry(
                            source_path=pdf_path,
                            content_hash=file_hash,
                            status="error",
                            retry_count=retry_count,
                            last_seen_at=_now(),
                            last_indexed_at=None,
                            error_message="Conversion timed out",
                            embedding_model=self._request.embedding_model,
                            embedding_status=None,
                            embedding_error=None,
                        )
                        processed += 1
                        self.progress.emit(processed, total, pdf_path)

        return GlobalRagIndexResult(indexed=indexed, skipped=skipped, failed=failed)

    def _index_from_markdown(
        self,
        pdf_path: str,
        file_hash: str,
        file_size: int,
        markdown: str,
        source_name: str,
        existing: Optional[object],
    ) -> bool:
        request = RagIndexRequest(
            workspace_id=self._request.workspace_id,
            session_id=None,
            artifact_entry_id=None,
            source_type="pdf",
            source_name=source_name,
            source_path=pdf_path,
            file_size=file_size,
            content=markdown,
            chunk_size_chars=self._request.chunk_size_chars,
            chunk_overlap_chars=self._request.chunk_overlap_chars,
            embedding_model=self._request.embedding_model,
            embeddings_enabled=self._request.embeddings_enabled,
            api_key=self._request.api_key,
        )
        index_result = _index_document(
            self._repository,
            request,
            self._chroma_service,
            embedding_cache=self._embedding_cache,
        )
        if index_result.success:
            self._repository.upsert_registry_entry(
                source_path=pdf_path,
                content_hash=file_hash,
                status="indexed",
                retry_count=0,
                last_seen_at=_now(),
                last_indexed_at=_now(),
                error_message=None,
                embedding_model=self._request.embedding_model,
                embedding_status=index_result.embedding_status,
                embedding_error=index_result.embedding_error or None,
            )
            return True
        retry_count = (existing.retry_count + 1) if existing else 1
        self._repository.upsert_registry_entry(
            source_path=pdf_path,
            content_hash=file_hash,
            status="error",
            retry_count=retry_count,
            last_seen_at=_now(),
            last_indexed_at=None,
            error_message=index_result.error_message,
            embedding_model=self._request.embedding_model,
            embedding_status=index_result.embedding_status,
            embedding_error=index_result.embedding_error or None,
        )
        return False


class GlobalRagService(QObject):
    """Service for indexing a global PDF library."""

    index_progress = Signal(int, int, str)
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
        self._worker: Optional[_GlobalIndexWorker] = None

    def index_paths(self, request: GlobalRagIndexRequest) -> None:
        if self.is_busy():
            self.index_error.emit("Global RAG indexing already in progress")
            return
        self._thread = QThread()
        self._worker = _GlobalIndexWorker(self._repository, request, self._chroma_service)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.index_progress)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._on_worker_error)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup)
        self._thread.start()

    def index_folder(self, folder_path: str, request: GlobalRagIndexRequest) -> None:
        folder = Path(folder_path).expanduser()
        pdf_paths = sorted(str(path) for path in folder.rglob("*.pdf"))
        self.index_paths(
            GlobalRagIndexRequest(
                workspace_id=request.workspace_id,
                pdf_paths=pdf_paths,
                chunk_size_chars=request.chunk_size_chars,
                chunk_overlap_chars=request.chunk_overlap_chars,
                embedding_model=request.embedding_model,
                embeddings_enabled=request.embeddings_enabled,
                api_key=request.api_key,
                force_reindex=request.force_reindex,
            )
        )

    def is_busy(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def get_registry_entries(self, status: Optional[str] = None):
        return self._repository.list_registry_entries(status=status)

    def get_registry_status_counts(self) -> dict[str, int]:
        return self._repository.get_registry_status_counts()

    def _on_worker_finished(self, result: GlobalRagIndexResult) -> None:
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


def _hash_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _now():
    from datetime import datetime

    return datetime.now()


def _sorted_paths_by_size(paths: list[str]) -> list[str]:
    def _size(path: str) -> int:
        try:
            return Path(path).stat().st_size
        except OSError:
            return 0

    return sorted(paths, key=_size)


def _batch_items(items: list[tuple], size: int):
    for index in range(0, len(items), size):
        yield items[index : index + size]
