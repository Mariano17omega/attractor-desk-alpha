"""Local ChatPDF indexing service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from pathlib import Path
from typing import Optional
from uuid import uuid4

from PySide6.QtCore import QObject, QThread, Signal

from core.persistence.rag_repository import RagRepository
from core.services.docling_service import convert_pdf_to_markdown
from core.services.rag_service import RagIndexRequest, _index_document

logger = logging.getLogger(__name__)

CHATPDF_STORAGE_DIR = Path.home() / ".open_canvas" / "chatpdf"


@dataclass(frozen=True)
class LocalRagIndexRequest:
    """Payload describing a ChatPDF upload to index."""

    workspace_id: str
    session_id: str
    pdf_path: str
    chunk_size_chars: int = 1200
    chunk_overlap_chars: int = 150
    embedding_model: Optional[str] = None
    embeddings_enabled: bool = False
    api_key: Optional[str] = None


@dataclass(frozen=True)
class LocalRagIndexResult:
    """Result for a ChatPDF indexing run."""

    success: bool
    document_id: Optional[str]
    saved_path: Optional[str]
    error_message: str = ""


class _LocalIndexWorker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def __init__(
        self,
        repository: RagRepository,
        request: LocalRagIndexRequest,
        chroma_service: Optional["ChromaService"] = None,
    ):
        super().__init__()
        self._repository = repository
        self._request = request
        self._chroma_service = chroma_service

    def run(self) -> None:
        try:
            result = self._run_index()
            self.finished.emit(result)
        except Exception as exc:
            logger.exception("ChatPDF indexing failed")
            self.error.emit(str(exc))

    def _run_index(self) -> LocalRagIndexResult:
        source_path = Path(self._request.pdf_path)
        if not source_path.exists() or not source_path.is_file():
            return LocalRagIndexResult(
                success=False,
                document_id=None,
                saved_path=None,
                error_message="File not found",
            )
        saved_path = _save_session_pdf(self._request.session_id, source_path)
        conversion = convert_pdf_to_markdown(str(saved_path))
        if not conversion.success:
            return LocalRagIndexResult(
                success=False,
                document_id=None,
                saved_path=str(saved_path),
                error_message=conversion.error_message,
            )
        request = RagIndexRequest(
            workspace_id=self._request.workspace_id,
            session_id=self._request.session_id,
            artifact_entry_id=None,
            source_type="chatpdf",
            source_name=conversion.source_filename,
            source_path=str(saved_path),
            file_size=saved_path.stat().st_size,
            content=conversion.markdown,
            chunk_size_chars=self._request.chunk_size_chars,
            chunk_overlap_chars=self._request.chunk_overlap_chars,
            embedding_model=self._request.embedding_model,
            embeddings_enabled=self._request.embeddings_enabled,
            api_key=self._request.api_key,
        )
        index_result = _index_document(self._repository, request, self._chroma_service)
        if not index_result.success:
            return LocalRagIndexResult(
                success=False,
                document_id=None,
                saved_path=str(saved_path),
                error_message=index_result.error_message,
            )
        return LocalRagIndexResult(
            success=True,
            document_id=index_result.document_id,
            saved_path=str(saved_path),
            error_message="",
        )


class LocalRagService(QObject):
    """Service for indexing ChatPDF uploads and cleanup."""

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
        self._worker: Optional[_LocalIndexWorker] = None

    def index_pdf(self, request: LocalRagIndexRequest) -> None:
        if self.is_busy():
            self.index_error.emit("ChatPDF indexing already in progress")
            return
        self._thread = QThread()
        self._worker = _LocalIndexWorker(self._repository, request, self._chroma_service)
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

    def mark_session_stale(self, session_id: str) -> None:
        self._repository.mark_session_documents_stale(session_id, datetime.now())

    def cleanup_stale_documents(self, retention_days: int) -> int:
        cutoff = datetime.now() - timedelta(days=retention_days)
        stale_docs = self._repository.list_stale_documents(cutoff)
        removed = 0
        for doc in stale_docs:
            if doc.source_path:
                try:
                    Path(doc.source_path).unlink(missing_ok=True)
                except OSError as exc:
                    logger.warning("Failed to delete %s: %s", doc.source_path, exc)

            # Delete from SQLite
            self._repository.delete_document(doc.id)

            # Also delete from ChromaDB (if available)
            if self._chroma_service is not None:
                try:
                    self._chroma_service.delete_by_document(doc.id)
                except Exception as exc:
                    logger.warning(f"Failed to delete document {doc.id} from ChromaDB: {exc}")

            removed += 1
        return removed

    def _on_worker_finished(self, result: LocalRagIndexResult) -> None:
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


def _save_session_pdf(session_id: str, source_path: Path) -> Path:
    session_dir = CHATPDF_STORAGE_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    suffix = source_path.suffix.lower() or ".pdf"
    filename = f"{source_path.stem}-{uuid4().hex}{suffix}"
    destination = session_dir / filename
    destination.write_bytes(source_path.read_bytes())
    return destination
