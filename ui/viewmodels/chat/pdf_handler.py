"""PdfHandler - Manages PDF import and conversion to text artifacts."""

from __future__ import annotations

from typing import Optional
from uuid import uuid4

from PySide6.QtCore import QObject, Signal, Slot

from core.persistence import ArtifactRepository
from core.services.docling_service import DoclingService, PdfConversionResult
from core.types import (
    ArtifactCollectionV1,
    ArtifactEntry,
    ArtifactExportMeta,
    ArtifactMarkdownV3,
    ArtifactV3,
)
from ui.viewmodels.chat.artifact_viewmodel import ArtifactViewModel
from ui.viewmodels.chat.rag_orchestrator import RagOrchestrator


class PdfHandler(QObject):
    """
    Handles PDF import, conversion, and artifact creation.

    Responsibilities:
    - Convert PDFs to Markdown via DoclingService
    - Create text artifacts from converted PDFs
    - Trigger RAG indexing for imported PDFs
    - Manage PDF conversion state and errors
    """

    pdf_import_status = Signal(str)
    error_occurred = Signal(str)

    def __init__(
        self,
        artifact_repository: ArtifactRepository,
        artifact_viewmodel: ArtifactViewModel,
        rag_orchestrator: RagOrchestrator,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._artifact_repository = artifact_repository
        self._artifact_viewmodel = artifact_viewmodel
        self._rag_orchestrator = rag_orchestrator

        # Docling service for PDF conversion
        self._docling_service = DoclingService(self)
        self._docling_service.conversion_complete.connect(self._on_pdf_conversion_complete)

        # Track pending PDF path for RAG indexing
        self._pending_pdf_path: Optional[str] = None
        self._current_workspace_id: Optional[str] = None
        self._current_session_id: Optional[str] = None

    @Slot(str)
    def import_pdf(
        self,
        pdf_path: str,
        workspace_id: str,
        session_id: str,
    ) -> None:
        """
        Start importing a PDF file as a new text artifact.

        Args:
            pdf_path: Absolute path to the PDF file
            workspace_id: The workspace ID
            session_id: The session ID
        """
        if self._docling_service.is_busy():
            self.error_occurred.emit("A PDF conversion is already in progress")
            return

        self.pdf_import_status.emit(f"Converting PDF: {pdf_path}")
        self._pending_pdf_path = pdf_path
        self._current_workspace_id = workspace_id
        self._current_session_id = session_id
        self._docling_service.convert_pdf(pdf_path)

    def _on_pdf_conversion_complete(self, result: PdfConversionResult) -> None:
        """
        Handle completed PDF conversion and create artifact.

        Args:
            result: Conversion result from DoclingService
        """
        if not result.success:
            self.error_occurred.emit(result.error_message)
            self.pdf_import_status.emit("")
            self._cleanup_conversion_state()
            return

        if not self._current_session_id:
            self.error_occurred.emit("No active session")
            self.pdf_import_status.emit("")
            self._cleanup_conversion_state()
            return

        # Create a new text artifact from the converted Markdown
        markdown_content = ArtifactMarkdownV3(
            index=1,
            type="text",
            title=result.source_filename,
            fullMarkdown=result.markdown,
        )
        new_artifact = ArtifactV3(
            currentIndex=1,
            contents=[markdown_content],
        )
        entry = ArtifactEntry(
            id=str(uuid4()),
            artifact=new_artifact,
            export_meta=ArtifactExportMeta(source_pdf=result.source_filename),
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

        # Update current artifact reference and emit signal
        self._artifact_viewmodel.set_artifact(new_artifact)
        self.pdf_import_status.emit(f"Imported: {result.source_filename}")

        # Index the PDF artifact for RAG
        if self._current_workspace_id:
            self._rag_orchestrator.index_pdf_artifact(
                workspace_id=self._current_workspace_id,
                session_id=self._current_session_id,
                entry_id=entry.id,
                source_name=result.source_filename,
                content=result.markdown,
                source_path=self._pending_pdf_path,
            )

        self._cleanup_conversion_state()

    def _cleanup_conversion_state(self) -> None:
        """Clean up temporary state after conversion completes or fails."""
        self._pending_pdf_path = None
        self._current_workspace_id = None
        self._current_session_id = None

    def is_busy(self) -> bool:
        """Check if a PDF conversion is currently in progress."""
        return self._docling_service.is_busy()
