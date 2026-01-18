"""ChatPdfService - Manages ChatPDF mode for single-PDF chat sessions."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from uuid import uuid4

from PySide6.QtCore import QObject, Signal, Slot

from core.constants import DEFAULT_EMBEDDING_MODEL
from core.persistence import ArtifactRepository
from core.services.local_rag_service import (
    LocalRagService,
    LocalRagIndexRequest,
    LocalRagIndexResult,
)
from core.types import (
    ArtifactCollectionV1,
    ArtifactEntry,
    ArtifactExportMeta,
    ArtifactPdfV1,
    ArtifactV3,
)
from ui.viewmodels.chat.artifact_viewmodel import ArtifactViewModel
from ui.viewmodels.settings.coordinator import SettingsCoordinator as SettingsViewModel


class ChatPdfService(QObject):
    """
    Manages ChatPDF mode for interactive PDF chat sessions.

    ChatPDF is a specialized mode where:
    - A single PDF is uploaded and indexed in isolation
    - RAG retrieval is scoped only to that PDF's content
    - Conversation mode switches to 'chatpdf'
    - PDF artifact is created with embedded RAG document ID

    Responsibilities:
    - Initiate PDF indexing via LocalRagService
    - Create PDF artifacts with RAG metadata
    - Update conversation mode to ChatPDF
    - Handle indexing status and errors
    """

    chatpdf_status = Signal(str)
    error_occurred = Signal(str)

    def __init__(
        self,
        local_rag_service: Optional[LocalRagService],
        artifact_repository: ArtifactRepository,
        artifact_viewmodel: ArtifactViewModel,
        settings_viewmodel: SettingsViewModel,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._local_rag_service = local_rag_service
        self._artifact_repository = artifact_repository
        self._artifact_viewmodel = artifact_viewmodel
        self._settings_viewmodel = settings_viewmodel

        # Track pending PDF path
        self._pending_chatpdf_path: Optional[str] = None
        self._current_workspace_id: Optional[str] = None
        self._current_session_id: Optional[str] = None

        # Connect signals if service is available
        if self._local_rag_service:
            self._local_rag_service.index_complete.connect(self._on_index_complete)
            self._local_rag_service.index_error.connect(self._on_index_error)

    @Slot(str)
    def open_chatpdf(
        self,
        pdf_path: str,
        workspace_id: str,
        session_id: str,
    ) -> None:
        """
        Open a PDF in ChatPDF mode.

        Args:
            pdf_path: Path to the PDF file
            workspace_id: The workspace ID
            session_id: The session ID
        """
        if not self._local_rag_service:
            self.error_occurred.emit("ChatPDF service unavailable")
            return

        if self._local_rag_service.is_busy():
            self.error_occurred.emit("A ChatPDF indexing job is already in progress")
            return

        self.chatpdf_status.emit(f"Indexing PDF: {pdf_path}")
        self._pending_chatpdf_path = pdf_path
        self._current_workspace_id = workspace_id
        self._current_session_id = session_id

        request = LocalRagIndexRequest(
            workspace_id=workspace_id,
            session_id=session_id,
            pdf_path=pdf_path,
            chunk_size_chars=self._settings_viewmodel.rag_chunk_size_chars,
            chunk_overlap_chars=self._settings_viewmodel.rag_chunk_overlap_chars,
            embedding_model=self._settings_viewmodel.rag_embedding_model
            or DEFAULT_EMBEDDING_MODEL,
            embeddings_enabled=self._settings_viewmodel.rag_enabled
            and self._settings_viewmodel.rag_k_vec > 0,
            api_key=self._settings_viewmodel.api_key or None,
        )
        self._local_rag_service.index_pdf(request)

    def _on_index_complete(self, result: LocalRagIndexResult) -> None:
        """
        Handle completed PDF indexing.

        Args:
            result: Indexing result from LocalRagService
        """
        if not result.success:
            self.error_occurred.emit(result.error_message)
            self.chatpdf_status.emit("")
            self._cleanup_state()
            return

        if not self._current_session_id:
            self.error_occurred.emit("No active session")
            self.chatpdf_status.emit("")
            self._cleanup_state()
            return

        # Create PDF artifact with RAG metadata
        pdf_title = Path(result.saved_path).stem if result.saved_path else "PDF"
        pdf_content = ArtifactPdfV1(
            index=1,
            type="pdf",
            title=pdf_title,
            pdfPath=result.saved_path or "",
            totalPages=None,
            currentPage=1,
            ragDocumentId=result.document_id,
        )
        new_artifact = ArtifactV3(
            currentIndex=1,
            contents=[pdf_content],
        )
        entry = ArtifactEntry(
            id=str(uuid4()),
            artifact=new_artifact,
            export_meta=ArtifactExportMeta(),
        )

        # Add to collection or create new collection
        collection = self._artifact_repository.get_collection(self._current_session_id)
        if collection is None:
            collection = ArtifactCollectionV1(
                version=1,
                artifacts=[entry],
                active_artifact_id=entry.id,
            )
        else:
            collection.artifacts.append(entry)
            collection.active_artifact_id = entry.id

        self._artifact_repository.save_collection(self._current_session_id, collection)

        # Update artifact viewmodel and switch to ChatPDF mode
        self._artifact_viewmodel.set_artifact(new_artifact)
        self._artifact_viewmodel._conversation_mode = "chatpdf"
        self._artifact_viewmodel._active_pdf_document_id = result.document_id

        self.chatpdf_status.emit(f"ChatPDF ready: {pdf_title}")
        self._cleanup_state()

    def _on_index_error(self, error: str) -> None:
        """
        Handle PDF indexing error.

        Args:
            error: Error message
        """
        self.error_occurred.emit(error)
        self.chatpdf_status.emit("")
        self._cleanup_state()

    def _cleanup_state(self) -> None:
        """Clean up temporary state after indexing completes or fails."""
        self._pending_chatpdf_path = None
        self._current_workspace_id = None
        self._current_session_id = None

    def is_busy(self) -> bool:
        """Check if a ChatPDF indexing operation is in progress."""
        return (
            self._local_rag_service.is_busy() if self._local_rag_service else False
        )
