"""ChatPDFCleanupService - Stale ChatPDF document cleanup."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from PySide6.QtCore import QObject, QTimer, Signal

from core.persistence import Database, RagRepository

if TYPE_CHECKING:
    from core.services.chroma_service import ChromaService
    from .rag_configuration_settings import RAGConfigurationSettings

logger = logging.getLogger(__name__)


class ChatPDFCleanupService(QObject):
    """
    Manages automatic cleanup of stale ChatPDF documents.

    Runs periodic cleanup based on retention days configuration.
    """

    chatpdf_cleanup_complete = Signal(int)  # Number of documents removed

    def __init__(
        self,
        rag_config: "RAGConfigurationSettings",
        database: Optional[Database] = None,
        chroma_service: Optional["ChromaService"] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._rag_config = rag_config
        self._db = database or Database()
        self._chroma_service = chroma_service
        self._rag_repository = RagRepository(self._db)

        # Setup periodic cleanup timer (24 hours)
        self._cleanup_timer = QTimer(self)
        self._cleanup_timer.setInterval(24 * 60 * 60 * 1000)  # 24 hours in ms
        self._cleanup_timer.timeout.connect(self._run_cleanup)
        self._cleanup_timer.start()

    def cleanup_chatpdf_documents(self) -> int:
        """
        Manually trigger ChatPDF cleanup.

        Returns:
            Number of documents removed.
        """
        removed = self._run_cleanup()
        self.chatpdf_cleanup_complete.emit(removed)
        return removed

    def _run_cleanup(self) -> int:
        """
        Run cleanup of stale ChatPDF documents.

        Deletes documents older than retention days from:
        - Filesystem (PDF files)
        - SQLite database
        - ChromaDB (if available)

        Returns:
            Number of documents removed.
        """
        retention_days = self._rag_config.rag_chatpdf_retention_days
        cutoff = datetime.now() - timedelta(days=retention_days)
        stale_docs = self._rag_repository.list_stale_documents(cutoff)

        removed = 0
        for doc in stale_docs:
            # Delete PDF file from filesystem
            if doc.source_path:
                try:
                    Path(doc.source_path).unlink(missing_ok=True)
                except OSError as exc:
                    logger.warning(
                        f"Failed to delete file {doc.source_path}: {exc}"
                    )

            # Delete from SQLite
            try:
                self._rag_repository.delete_document(doc.id)
            except Exception as exc:
                logger.error(
                    f"Failed to delete document {doc.id} from database: {exc}"
                )
                continue

            # Delete from ChromaDB (if available)
            if self._chroma_service is not None:
                try:
                    self._chroma_service.delete_by_document(doc.id)
                except Exception as exc:
                    logger.warning(
                        f"Failed to delete document {doc.id} from ChromaDB: {exc}"
                    )

            removed += 1

        if removed > 0:
            logger.info(
                f"Cleaned up {removed} stale ChatPDF documents "
                f"(older than {retention_days} days)"
            )

        return removed

    def stop(self) -> None:
        """Stop the cleanup timer (e.g., on application shutdown)."""
        if self._cleanup_timer.isActive():
            self._cleanup_timer.stop()
