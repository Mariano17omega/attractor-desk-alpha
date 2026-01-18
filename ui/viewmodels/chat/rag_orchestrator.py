"""RagOrchestrator - Manages background RAG indexing operations."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject

from core.constants import DEFAULT_EMBEDDING_MODEL
from core.persistence import ArtifactRepository
from core.services.rag_service import RagIndexRequest, RagService
from ui.viewmodels.settings.coordinator import SettingsCoordinator as SettingsViewModel


class RagOrchestrator(QObject):
    """
    Orchestrates background RAG indexing for PDF and text artifacts.

    Responsibilities:
    - Index PDF artifacts after conversion
    - Index active text artifacts when configured
    - Build RagIndexRequest with proper configuration
    - Fire-and-forget background indexing (no signals)
    """

    def __init__(
        self,
        rag_service: Optional[RagService],
        artifact_repository: ArtifactRepository,
        settings_viewmodel: SettingsViewModel,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._rag_service = rag_service
        self._artifact_repository = artifact_repository
        self._settings_viewmodel = settings_viewmodel

    def index_pdf_artifact(
        self,
        workspace_id: str,
        session_id: str,
        entry_id: str,
        source_name: str,
        content: str,
        source_path: Optional[str] = None,
    ) -> None:
        """
        Index a PDF artifact for global RAG retrieval.

        Args:
            workspace_id: The workspace ID
            session_id: The session ID
            entry_id: The artifact entry ID
            source_name: Display name for the PDF
            content: Converted Markdown content from PDF
            source_path: Optional path to the original PDF file
        """
        if not self._rag_service:
            return

        request = RagIndexRequest(
            workspace_id=workspace_id,
            session_id=session_id,
            artifact_entry_id=entry_id,
            source_type="pdf",
            source_name=source_name,
            source_path=source_path,
            content=content,
            chunk_size_chars=self._settings_viewmodel.rag_chunk_size_chars,
            chunk_overlap_chars=self._settings_viewmodel.rag_chunk_overlap_chars,
            embedding_model=self._settings_viewmodel.rag_embedding_model
            or DEFAULT_EMBEDDING_MODEL,
            embeddings_enabled=self._settings_viewmodel.rag_enabled
            and self._settings_viewmodel.rag_k_vec > 0,
            api_key=self._settings_viewmodel.api_key or None,
        )
        self._rag_service.index_artifact(request)

    def index_active_text_artifact(
        self,
        workspace_id: str,
        session_id: str,
    ) -> None:
        """
        Index the active text artifact for global RAG retrieval.

        Only indexes if:
        - RAG service is available
        - Text artifact indexing is enabled in settings
        - Session has an active artifact
        - Active artifact is of type 'text'

        Args:
            workspace_id: The workspace ID
            session_id: The session ID
        """
        if not self._rag_service:
            return

        if not self._settings_viewmodel.rag_index_text_artifacts:
            return

        collection = self._artifact_repository.get_collection(session_id)
        if collection is None:
            return

        entry = collection.get_active_entry()
        if entry is None or not entry.artifact.contents:
            return

        current_content = entry.artifact.contents[-1]
        if getattr(current_content, "type", "") != "text":
            return

        source_name = current_content.title or "Untitled"
        request = RagIndexRequest(
            workspace_id=workspace_id,
            session_id=session_id,
            artifact_entry_id=entry.id,
            source_type="artifact",
            source_name=source_name,
            content=current_content.full_markdown,
            chunk_size_chars=self._settings_viewmodel.rag_chunk_size_chars,
            chunk_overlap_chars=self._settings_viewmodel.rag_chunk_overlap_chars,
            embedding_model=self._settings_viewmodel.rag_embedding_model
            or DEFAULT_EMBEDDING_MODEL,
            embeddings_enabled=self._settings_viewmodel.rag_enabled
            and self._settings_viewmodel.rag_k_vec > 0,
            api_key=self._settings_viewmodel.api_key or None,
        )
        self._rag_service.index_artifact(request)
