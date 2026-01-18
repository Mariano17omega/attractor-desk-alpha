"""ChatCoordinator - Facade coordinating all chat subsystems."""

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot

from core.persistence import (
    ArtifactRepository,
    MessageAttachmentRepository,
    MessageRepository,
    SessionRepository,
)
from core.services.rag_service import RagService
from core.services.local_rag_service import LocalRagService
from core.types import ArtifactV3
from ui.viewmodels.settings.coordinator import SettingsCoordinator as SettingsViewModel
from ui.viewmodels.chat.artifact_viewmodel import ArtifactViewModel
from ui.viewmodels.chat.rag_orchestrator import RagOrchestrator
from ui.viewmodels.chat.pdf_handler import PdfHandler
from ui.viewmodels.chat.chatpdf_service import ChatPdfService
from ui.viewmodels.chat.graph_execution_handler import GraphExecutionHandler
from ui.viewmodels.chat.session_manager import SessionManager

logger = logging.getLogger(__name__)


class ChatCoordinator(QObject):
    """Facade coordinating all chat subsystems.

    This coordinator provides a unified interface to all chat functionality by
    delegating to specialized subsystems:
    - SessionManager: Session lifecycle and message state
    - ArtifactViewModel: Artifact state and versioning
    - RagOrchestrator: RAG indexing coordination
    - PdfHandler: PDF conversion and import
    - ChatPdfService: ChatPDF mode management
    - GraphExecutionHandler: LangGraph execution and message orchestration

    All signals from subsystems are forwarded for backward compatibility.
    """

    # Forwarded signals from subsystems
    message_added = Signal(str, bool)
    messages_loaded = Signal(object)
    artifact_changed = Signal()
    is_loading_changed = Signal(bool)
    status_changed = Signal(str)
    error_occurred = Signal(str)
    session_updated = Signal()
    pdf_import_status = Signal(str)
    chatpdf_status = Signal(str)
    pending_attachments_changed = Signal(object)

    def __init__(
        self,
        message_repository: MessageRepository,
        attachment_repository: MessageAttachmentRepository,
        artifact_repository: ArtifactRepository,
        session_repository: SessionRepository,
        settings_viewmodel: SettingsViewModel,
        rag_service: Optional[RagService] = None,
        local_rag_service: Optional[LocalRagService] = None,
        parent: Optional[QObject] = None,
    ):
        """Initialize the chat coordinator.

        Args:
            message_repository: Repository for message persistence
            attachment_repository: Repository for message attachment persistence
            artifact_repository: Repository for artifact persistence
            session_repository: Repository for session persistence
            settings_viewmodel: Settings viewmodel for configuration
            rag_service: Optional RAG service for global indexing
            local_rag_service: Optional local RAG service for ChatPDF
            parent: Optional parent QObject
        """
        super().__init__(parent)

        # Store dependencies
        self._local_rag_service = local_rag_service
        self._pending_attachments: list[str] = []

        # Initialize subsystems

        # Session management
        self.sessions = SessionManager(
            session_repository=session_repository,
            message_repository=message_repository,
            parent=self,
        )

        # Artifact management
        self.artifacts = ArtifactViewModel(
            artifact_repository=artifact_repository,
            parent=self,
        )

        # RAG indexing orchestration
        self.rag = RagOrchestrator(
            rag_service=rag_service,
            artifact_repository=artifact_repository,
            settings_viewmodel=settings_viewmodel,
            parent=self,
        )

        # PDF import handler
        self.pdf = PdfHandler(
            artifact_repository=artifact_repository,
            artifact_viewmodel=self.artifacts,
            rag_orchestrator=self.rag,
            parent=self,
        )

        # ChatPDF service
        self.chatpdf = ChatPdfService(
            local_rag_service=local_rag_service,
            artifact_repository=artifact_repository,
            artifact_viewmodel=self.artifacts,
            settings_viewmodel=settings_viewmodel,
            parent=self,
        )

        # Graph execution handler
        self.graph = GraphExecutionHandler(
            message_repository=message_repository,
            attachment_repository=attachment_repository,
            artifact_repository=artifact_repository,
            session_repository=session_repository,
            settings_viewmodel=settings_viewmodel,
            artifact_viewmodel=self.artifacts,
            rag_orchestrator=self.rag,
            parent=self,
        )

        # Wire up signal forwarding
        self._connect_signals()

    def _connect_signals(self):
        """Forward signals from subsystems to coordinator signals."""
        # Session signals
        self.sessions.messages_loaded.connect(self.messages_loaded)
        self.sessions.session_updated.connect(self.session_updated)

        # Artifact signals
        self.artifacts.artifact_changed.connect(self.artifact_changed)

        # PDF handler signals
        self.pdf.pdf_import_status.connect(self.pdf_import_status)
        self.pdf.error_occurred.connect(self.error_occurred)

        # ChatPDF service signals
        self.chatpdf.chatpdf_status.connect(self.chatpdf_status)
        self.chatpdf.error_occurred.connect(self.error_occurred)

        # Graph execution signals
        self.graph.message_added.connect(self.message_added)
        self.graph.is_loading_changed.connect(self.is_loading_changed)
        self.graph.status_changed.connect(self.status_changed)
        self.graph.session_updated.connect(self.session_updated)
        self.graph.error_occurred.connect(self.error_occurred)

    # ========== Backward Compatibility Properties ==========

    @property
    def messages(self) -> list:
        """Get the current message list."""
        return self.sessions.messages

    @property
    def current_artifact(self) -> Optional[ArtifactV3]:
        """Get the current artifact."""
        return self.artifacts.current_artifact

    @property
    def is_loading(self) -> bool:
        """Check if currently loading."""
        return self.graph.is_loading

    @property
    def current_session_id(self) -> Optional[str]:
        """Get the current session ID."""
        return self.sessions.current_session_id

    @property
    def pending_attachments(self) -> list[str]:
        """Get pending attachments."""
        return self._pending_attachments.copy()

    # ========== Session Management Methods ==========

    def load_session(self, session_id: str) -> None:
        """Load a session and its messages.

        Args:
            session_id: The ID of the session to load
        """
        # Mark previous session stale if using ChatPDF
        if self.sessions.current_session and self._local_rag_service:
            self._local_rag_service.mark_session_stale(
                self.sessions.current_session.id
            )

        self._clear_pending_attachments()

        # Load session via session manager
        self.sessions.load_session(session_id)

        # Get the loaded session
        session = self.sessions.current_session
        if session is None:
            return

        # Update graph handler with session and messages
        self.graph.set_session(session)
        self.graph.set_messages(self.sessions.messages)

        # Load artifacts
        self.artifacts.load_artifact_for_session(session_id)

    def clear(self) -> None:
        """Clear the current session and messages."""
        # Mark session stale if using ChatPDF
        if self.sessions.current_session and self._local_rag_service:
            self._local_rag_service.mark_session_stale(
                self.sessions.current_session.id
            )

        # Clear session via session manager
        self.sessions.clear()

        # Clear graph handler state
        self.graph.set_session(None)
        self.graph.set_messages([])

        # Clear artifacts and attachments
        self.artifacts.clear_artifact()
        self._clear_pending_attachments()

    @Slot()
    def clear_conversation(self):
        """Clear the conversation history (UI-only)."""
        self.clear()

    # ========== Message Sending Methods ==========

    @Slot(str)
    def send_message(self, content: str):
        """Send a user message and run the graph.

        Args:
            content: The user's message content
        """
        if not self.sessions.current_session:
            return

        # Update graph handler with current session and pending attachments
        self.graph.set_session(self.sessions.current_session)
        self.graph.set_pending_attachments(self._pending_attachments)

        # Delegate to graph handler
        self.graph.send_message(content, self._clear_pending_attachments)

    @Slot()
    def cancel_generation(self):
        """Cancel the current generation (best-effort)."""
        self.graph.cancel_generation()

    # ========== Attachment Management ==========

    def add_pending_attachment(self, file_path: str) -> None:
        """Add a pending attachment.

        Args:
            file_path: Path to the attachment file
        """
        if not self.sessions.current_session:
            self.error_occurred.emit("No active session for attachments")
            return
        if not file_path:
            return
        path = Path(file_path)
        if not path.exists():
            self.error_occurred.emit("Attachment file not found")
            return
        normalized = str(path)
        if normalized in self._pending_attachments:
            return
        self._pending_attachments.append(normalized)
        self.pending_attachments_changed.emit(self._pending_attachments.copy())

    def _clear_pending_attachments(self) -> None:
        """Clear pending attachments."""
        if not self._pending_attachments:
            return
        self._pending_attachments = []
        self.pending_attachments_changed.emit([])

    # ========== Artifact Navigation ==========

    @Slot()
    def prev_artifact_version(self):
        """Navigate to previous artifact version."""
        self.artifacts.prev_artifact_version()

    @Slot()
    def next_artifact_version(self):
        """Navigate to next artifact version."""
        self.artifacts.next_artifact_version()

    def on_artifact_selected(self, artifact_id: str) -> None:
        """Handle artifact selection.

        Args:
            artifact_id: The ID of the selected artifact
        """
        if not self.sessions.current_session:
            return
        self.artifacts.on_artifact_selected(
            artifact_id, self.sessions.current_session.id
        )

    # ========== PDF Import Methods ==========

    @Slot(str)
    def import_pdf(self, pdf_path: str) -> None:
        """Start importing a PDF file as a new text artifact.

        Args:
            pdf_path: Absolute path to the PDF file
        """
        if not self.sessions.current_session:
            self.error_occurred.emit("No active session for PDF import")
            return

        self.pdf.import_pdf(
            pdf_path=pdf_path,
            workspace_id=self.sessions.current_session.workspace_id,
            session_id=self.sessions.current_session.id,
        )

    @Slot(str)
    def open_chatpdf(self, pdf_path: str) -> None:
        """Open a PDF in ChatPDF mode.

        Args:
            pdf_path: Path to the PDF file
        """
        if not self.sessions.current_session:
            self.error_occurred.emit("No active session for ChatPDF")
            return

        self.chatpdf.open_chatpdf(
            pdf_path=pdf_path,
            workspace_id=self.sessions.current_session.workspace_id,
            session_id=self.sessions.current_session.id,
        )
