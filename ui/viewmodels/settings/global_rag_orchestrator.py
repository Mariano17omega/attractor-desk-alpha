"""GlobalRAGOrchestrator - Global RAG indexing and monitoring operations."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from core.constants import DEFAULT_EMBEDDING_MODEL
from core.persistence import Database, RagRepository
from core.persistence.rag_repository import GLOBAL_WORKSPACE_ID
from core.services import GlobalRagService, GlobalRagIndexRequest, PdfWatcherService

if TYPE_CHECKING:
    from core.services.chroma_service import ChromaService
    from .model_settings import ModelSettings
    from .rag_configuration_settings import RAGConfigurationSettings


class GlobalRAGOrchestrator(QObject):
    """
    Orchestrates Global RAG indexing, monitoring, and registry management.

    Handles side effects that were previously in RAGConfigurationSettings setters.
    """

    global_rag_progress = Signal(int, int, str)  # current, total, path
    global_rag_complete = Signal(object)
    global_rag_error = Signal(str)
    global_rag_registry_updated = Signal()

    def __init__(
        self,
        rag_config: "RAGConfigurationSettings",
        model_settings: "ModelSettings",
        database: Optional[Database] = None,
        chroma_service: Optional["ChromaService"] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._rag_config = rag_config
        self._model_settings = model_settings
        self._db = database or Database()
        self._chroma_service = chroma_service

        # Initialize services
        self._rag_repository = RagRepository(self._db)
        self._global_rag_service = GlobalRagService(
            self._rag_repository, chroma_service, self
        )
        self._pdf_watcher_service = PdfWatcherService(self)

        # Wire up signals
        self._global_rag_service.index_progress.connect(self._on_index_progress)
        self._global_rag_service.index_complete.connect(self._on_index_complete)
        self._global_rag_service.index_error.connect(self._on_index_error)
        self._pdf_watcher_service.new_pdfs_detected.connect(self._on_pdfs_detected)
        self._pdf_watcher_service.watcher_error.connect(self.global_rag_error.emit)

        # Connect to config changes for monitoring management
        self._rag_config.settings_changed.connect(self._on_config_changed)

    def start_global_index(self, force_reindex: bool = False) -> None:
        """Start indexing the global RAG folder."""
        folder = self._rag_config.rag_global_folder
        if not folder:
            self.global_rag_error.emit("Global RAG folder is not set")
            return

        request = self._build_request(force_reindex=force_reindex)
        self._global_rag_service.index_folder(folder, request)

    def scan_global_folder(self) -> None:
        """Scan global folder for new documents (no force reindex)."""
        folder = self._rag_config.rag_global_folder
        if not folder:
            self.global_rag_error.emit("Global RAG folder is not set")
            return

        request = self._build_request(force_reindex=False)
        self._global_rag_service.index_folder(folder, request)

    def list_global_registry_entries(self, status: Optional[str] = None):
        """Get list of global registry entries, optionally filtered by status."""
        return self._global_rag_service.get_registry_entries(status=status)

    def get_global_registry_status_counts(self) -> dict[str, int]:
        """Get counts of registry entries by status."""
        return self._global_rag_service.get_registry_status_counts()

    def start_monitoring(self) -> None:
        """Start monitoring the global folder for new PDFs."""
        folder = self._rag_config.rag_global_folder
        if not folder:
            self.global_rag_error.emit("Global RAG folder is not set")
            return
        self._pdf_watcher_service.start(folder)

    def stop_monitoring(self) -> None:
        """Stop monitoring the global folder."""
        self._pdf_watcher_service.stop()

    def update_monitoring_state(self) -> None:
        """
        Update monitoring state based on configuration.

        Called when monitoring toggle or folder path changes.
        """
        if self._rag_config.rag_global_monitoring_enabled:
            self.start_monitoring()
        else:
            self.stop_monitoring()

    def _build_request(self, force_reindex: bool) -> GlobalRagIndexRequest:
        """Build GlobalRagIndexRequest from current configuration."""
        return GlobalRagIndexRequest(
            workspace_id=GLOBAL_WORKSPACE_ID,
            pdf_paths=[],
            chunk_size_chars=self._rag_config.rag_chunk_size_chars,
            chunk_overlap_chars=self._rag_config.rag_chunk_overlap_chars,
            embedding_model=self._rag_config.rag_embedding_model or DEFAULT_EMBEDDING_MODEL,
            embeddings_enabled=self._rag_config.rag_enabled
            and self._rag_config.rag_k_vec > 0,
            api_key=self._model_settings.api_key or None,
            force_reindex=force_reindex,
        )

    def _on_config_changed(self) -> None:
        """Handle configuration changes to update monitoring."""
        # Note: This is called on ANY config change, so we check if monitoring-related
        # The actual monitoring state update happens when explicitly requested
        pass

    def _on_pdfs_detected(self, paths: list[str]) -> None:
        """Handle new PDFs detected by watcher."""
        if not paths:
            return

        request = self._build_request(force_reindex=False)
        self._global_rag_service.index_paths(
            GlobalRagIndexRequest(
                workspace_id=request.workspace_id,
                pdf_paths=paths,
                chunk_size_chars=request.chunk_size_chars,
                chunk_overlap_chars=request.chunk_overlap_chars,
                embedding_model=request.embedding_model,
                embeddings_enabled=request.embeddings_enabled,
                api_key=request.api_key,
                force_reindex=False,
            )
        )

    def _on_index_progress(self, current: int, total: int, path: str) -> None:
        """Forward indexing progress signal."""
        self.global_rag_progress.emit(current, total, path)

    def _on_index_complete(self, result: object) -> None:
        """Forward indexing complete signal and update registry."""
        self.global_rag_complete.emit(result)
        self.global_rag_registry_updated.emit()

    def _on_index_error(self, error: str) -> None:
        """Forward indexing error signal and update registry."""
        self.global_rag_error.emit(error)
        self.global_rag_registry_updated.emit()
