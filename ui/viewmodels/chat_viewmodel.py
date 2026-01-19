"""Chat ViewModel for Open Canvas - Backward compatibility wrapper."""

from typing import Optional

from core.persistence import (
    ArtifactRepository,
    Database,
    MessageAttachmentRepository,
    MessageRepository,
    SessionRepository,
)
from core.services.rag_service import RagService
from core.services.local_rag_service import LocalRagService
from ui.viewmodels.settings.coordinator import SettingsCoordinator as SettingsViewModel
from ui.viewmodels.chat.coordinator import ChatCoordinator


class ChatViewModel(ChatCoordinator):
    """ViewModel for the chat interface.

    This class now serves as a backward compatibility wrapper around ChatCoordinator.
    All functionality has been delegated to specialized subsystems:
    - SessionManager: Session lifecycle
    - ArtifactViewModel: Artifact management
    - RagOrchestrator: RAG indexing
    - PdfHandler: PDF import
    - ChatPdfService: ChatPDF mode
    - GraphExecutionHandler: Graph execution

    The ChatViewModel maintains the same public API for UI compatibility.
    """

    def __init__(
        self,
        message_repository: MessageRepository,
        attachment_repository: MessageAttachmentRepository,
        artifact_repository: ArtifactRepository,
        session_repository: SessionRepository,
        settings_viewmodel: SettingsViewModel,
        database: Optional[Database] = None,
        rag_service: Optional[RagService] = None,
        local_rag_service: Optional[LocalRagService] = None,
        parent=None,
    ):
        """Initialize the chat viewmodel.

        Args:
            message_repository: Repository for message persistence
            attachment_repository: Repository for message attachment persistence
            artifact_repository: Repository for artifact persistence
            session_repository: Repository for session persistence
            settings_viewmodel: Settings viewmodel for configuration
            database: Optional shared database instance for graph config
            rag_service: Optional RAG service for global indexing
            local_rag_service: Optional local RAG service for ChatPDF
            parent: Optional parent QObject
        """
        super().__init__(
            message_repository=message_repository,
            attachment_repository=attachment_repository,
            artifact_repository=artifact_repository,
            session_repository=session_repository,
            settings_viewmodel=settings_viewmodel,
            database=database,
            rag_service=rag_service,
            local_rag_service=local_rag_service,
            parent=parent,
        )
