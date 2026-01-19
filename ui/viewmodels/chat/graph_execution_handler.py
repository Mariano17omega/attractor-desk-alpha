"""GraphExecutionHandler - Manages LangGraph execution and message orchestration."""

import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from PySide6.QtCore import QObject, Signal, Slot
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from core.config import get_exa_api_key, get_firecrawl_api_key
from core.models import Message, MessageAttachment, MessageRole, Session
from core.persistence import (
    ArtifactRepository,
    Database,
    MessageAttachmentRepository,
    MessageRepository,
    SessionRepository,
)
from ui.services.image_utils import file_path_to_data_url
from ui.viewmodels.settings.coordinator import SettingsCoordinator as SettingsViewModel
from ui.viewmodels.chat.artifact_viewmodel import ArtifactViewModel
from ui.viewmodels.chat.rag_orchestrator import RagOrchestrator
from ui.viewmodels.chat.graph_worker import GraphWorker

logger = logging.getLogger(__name__)


class GraphExecutionHandler(QObject):
    """Handles graph execution and message orchestration.

    This class manages:
    - Sending messages to the LangGraph backend
    - Running the graph in a background worker thread
    - Processing graph results and updating artifacts
    - Managing loading state and error handling
    - Canceling in-progress generations

    Signals:
        message_added(str, bool): Emitted when a message is added (content, is_user)
        is_loading_changed(bool): Emitted when loading state changes
        status_changed(str): Emitted when status changes
        session_updated(): Emitted when session is updated (e.g., title change)
        error_occurred(str): Emitted when an error occurs
    """

    message_added = Signal(str, bool)
    is_loading_changed = Signal(bool)
    status_changed = Signal(str)
    session_updated = Signal()
    error_occurred = Signal(str)

    def __init__(
        self,
        message_repository: MessageRepository,
        attachment_repository: MessageAttachmentRepository,
        artifact_repository: ArtifactRepository,
        session_repository: SessionRepository,
        settings_viewmodel: SettingsViewModel,
        artifact_viewmodel: ArtifactViewModel,
        rag_orchestrator: RagOrchestrator,
        database: Optional[Database] = None,
        parent: Optional[QObject] = None,
    ):
        """Initialize the graph execution handler.

        Args:
            message_repository: Repository for message persistence
            attachment_repository: Repository for message attachment persistence
            artifact_repository: Repository for artifact persistence
            session_repository: Repository for session persistence
            settings_viewmodel: Settings viewmodel for configuration
            artifact_viewmodel: Artifact viewmodel for artifact state
            rag_orchestrator: RAG orchestrator for indexing
            database: Optional shared database instance for graph config
            parent: Optional parent QObject
        """
        super().__init__(parent)
        self._message_repository = message_repository
        self._attachment_repository = attachment_repository
        self._artifact_repository = artifact_repository
        self._session_repository = session_repository
        self._settings_viewmodel = settings_viewmodel
        self._artifact_viewmodel = artifact_viewmodel
        self._rag_orchestrator = rag_orchestrator
        self._database = database

        self._messages: list[BaseMessage] = []
        self._internal_messages: list[BaseMessage] = []
        self._is_loading: bool = False
        self._assistant_id: str = str(uuid4())
        self._current_session: Optional[Session] = None
        self._pending_attachments: list[str] = []

        self._worker: Optional[GraphWorker] = None
        self._active_run_token: Optional[str] = None
        self._active_session_id: Optional[str] = None  # Track session for race condition prevention

        self._settings: dict = {
            "model": "anthropic/claude-3.5-sonnet",
            "temperature": 0.5,
            "max_tokens": 4096,
            "streaming": True,
            "timeout": 120,
        }

    @property
    def is_loading(self) -> bool:
        """Check if currently loading."""
        return self._is_loading

    @property
    def messages(self) -> list[BaseMessage]:
        """Get the current message list."""
        return self._messages

    @property
    def internal_messages(self) -> list[BaseMessage]:
        """Get the internal message list."""
        return self._internal_messages

    def set_session(self, session: Optional[Session]) -> None:
        """Set the current session.

        Args:
            session: The session to set as current
        """
        self._current_session = session

    def set_messages(self, messages: list[BaseMessage]) -> None:
        """Set the message list.

        Args:
            messages: The messages to set
        """
        self._messages = messages
        self._internal_messages = messages.copy()

    def set_pending_attachments(self, attachments: list[str]) -> None:
        """Set pending attachments.

        Args:
            attachments: List of file paths for pending attachments
        """
        self._pending_attachments = attachments

    def _set_loading(self, loading: bool) -> None:
        """Set loading state.

        Args:
            loading: Whether loading is active
        """
        self._is_loading = loading
        self.is_loading_changed.emit(loading)

    @Slot(str)
    def send_message(self, content: str, clear_attachments_callback=None) -> None:
        """Send a user message and run the graph.

        Args:
            content: The user's message content
            clear_attachments_callback: Optional callback to clear pending attachments
        """
        if self._is_loading or not self._current_session:
            return

        user_record = Message.create(
            session_id=self._current_session.id,
            role=MessageRole.USER,
            content=content,
        )
        self._message_repository.add(user_record)

        attachments = self._pending_attachments.copy()
        content_payload: str | list[dict] = content
        attached_paths: list[str] = []
        if attachments:
            parts = [{"type": "text", "text": content}]
            for path in attachments:
                try:
                    data_url = file_path_to_data_url(path)
                except Exception as exc:
                    self.error_occurred.emit(f"Failed to attach image: {exc}")
                    continue
                parts.append({"type": "image_url", "image_url": {"url": data_url}})
                attached_paths.append(path)
            if attached_paths:
                content_payload = parts

        # Add user message
        user_message = HumanMessage(content=content_payload)
        self._messages.append(user_message)
        self._internal_messages.append(user_message)
        self.message_added.emit(content, True)

        now = datetime.now()
        if len(self._messages) == 1:
            new_title = content.strip()[:50] or "New Session"
            if self._current_session.title != new_title:
                self._current_session.title = new_title
        self._current_session.updated_at = now
        self._session_repository.update(self._current_session)
        self.session_updated.emit()

        if attached_paths:
            for path in attached_paths:
                attachment = MessageAttachment.create(user_record.id, path)
                self._attachment_repository.add(attachment)

        if clear_attachments_callback:
            clear_attachments_callback()

        # Start loading
        self._set_loading(True)
        self.status_changed.emit("Processing...")

        # Prepare state
        state = self._prepare_graph_state()

        # Prepare config
        config = self._prepare_graph_config()

        # Run in worker thread with a unique run token
        run_token = str(uuid4())
        self._active_run_token = run_token
        self._active_session_id = self._current_session.id  # Capture session for race condition check

        # Clean up any previous worker reference (worker is one-shot)
        # Note: The actual C++ object may already be deleted via deleteLater
        self._worker = None

        # Create new worker (one-shot pattern)
        self._worker = GraphWorker(state, config, run_token)
        self._worker.finished.connect(self._on_graph_finished)
        self._worker.error.connect(self._on_graph_error)
        self._worker.finished.connect(self._cleanup_worker)
        self._worker.error.connect(self._cleanup_worker)
        self._worker.start()

    def _cleanup_worker(self) -> None:
        """Clean up the worker after it finishes.

        This ensures we don't hold a reference to a deleted QThread.
        Called when the worker finishes (success or error).
        """
        if self._worker is not None:
            # Schedule the worker for deletion and clear our reference
            self._worker.deleteLater()
            self._worker = None

    def _prepare_graph_state(self) -> dict:
        """Prepare the state for graph execution.

        Returns:
            The state dictionary for the graph
        """
        internal_messages = (
            self._internal_messages.copy()
            if self._internal_messages
            else self._messages.copy()
        )
        state = {
            "messages": self._messages.copy(),
            "internal_messages": internal_messages,
            "web_search_enabled": self._settings_viewmodel.deep_search_enabled,
            "conversation_mode": self._artifact_viewmodel.conversation_mode,
            "active_pdf_document_id": self._artifact_viewmodel.active_pdf_document_id,
        }

        if self._artifact_viewmodel.current_artifact:
            state["artifact"] = self._artifact_viewmodel.current_artifact

        return state

    def _prepare_graph_config(self) -> dict:
        """Prepare the configuration for graph execution.

        Returns:
            The configuration dictionary for the graph
        """
        exa_api_key = self._settings_viewmodel.exa_api_key or get_exa_api_key()
        firecrawl_api_key = (
            self._settings_viewmodel.firecrawl_api_key or get_firecrawl_api_key()
        )

        config = {
            "configurable": {
                "assistant_id": self._assistant_id,
                "model": self._settings_viewmodel.default_model
                or self._settings.get("model", "anthropic/claude-3.5-sonnet"),
                "image_model": self._settings_viewmodel.image_model,
                "temperature": self._settings.get("temperature", 0.5),
                "max_tokens": self._settings.get("max_tokens", 4096),
                "api_key": self._settings_viewmodel.api_key or None,
                "session_id": self._current_session.id,
                "workspace_id": self._current_session.workspace_id,
                "database": self._database,  # Pass shared database instance for graph nodes
                "rag_enabled": self._settings_viewmodel.rag_enabled,
                "rag_scope": self._settings_viewmodel.rag_scope,
                "rag_k_lex": self._settings_viewmodel.rag_k_lex,
                "rag_k_vec": self._settings_viewmodel.rag_k_vec,
                "rag_rrf_k": self._settings_viewmodel.rag_rrf_k,
                "rag_max_candidates": self._settings_viewmodel.rag_max_candidates,
                "rag_embedding_model": self._settings_viewmodel.rag_embedding_model,
                "rag_enable_query_rewrite": self._settings_viewmodel.rag_enable_query_rewrite,
                "rag_enable_llm_rerank": self._settings_viewmodel.rag_enable_llm_rerank,
                "conversation_mode": self._artifact_viewmodel.conversation_mode,
                "active_pdf_document_id": self._artifact_viewmodel.active_pdf_document_id,
                "web_search_provider": self._settings_viewmodel.search_provider,
                "web_search_num_results": self._settings_viewmodel.deep_search_num_results,
                "exa_api_key": exa_api_key or None,
                "firecrawl_api_key": firecrawl_api_key or None,
            }
        }

        return config

    def _on_graph_finished(self, result: dict, run_token: str) -> None:
        """Handle successful graph execution.

        Args:
            result: The result from the graph execution
            run_token: The token identifying this execution run
        """
        # Ignore stale results from cancelled or outdated workers
        if run_token != self._active_run_token:
            return

        # Verify session hasn't changed during graph execution (race condition prevention)
        if not self._current_session or self._current_session.id != self._active_session_id:
            logger.info(
                "Ignoring graph result from session %s - current session is %s",
                self._active_session_id,
                self._current_session.id if self._current_session else "None",
            )
            return

        self._set_loading(False)
        self.status_changed.emit("Ready")

        # Debug: Print result keys
        logger.debug("Graph result keys: %s", list(result.keys()))

        internal_messages_from_result = False
        if "internal_messages" in result and result["internal_messages"] is not None:
            self._internal_messages = list(result["internal_messages"])
            internal_messages_from_result = True

        # Update artifact first
        if "artifact" in result and result["artifact"]:
            logger.debug("Artifact found in result: %s", type(result["artifact"]))
            self._artifact_viewmodel.set_artifact(result["artifact"])
            if self._current_session:
                self._artifact_repository.save_for_session(
                    self._current_session.id,
                    result["artifact"],
                )
                # Index the updated artifact
                self._rag_orchestrator.index_active_text_artifact(
                    workspace_id=self._current_session.workspace_id,
                    session_id=self._current_session.id,
                )
            logger.debug("Artifact emitted with %s contents", len(result["artifact"].contents))
        else:
            logger.debug(
                "No artifact in result. 'artifact' key exists: %s",
                "artifact" in result,
            )

        # Update messages with error handling
        if "messages" in result:
            new_messages = result["messages"]
            logger.debug("Messages in result: %s", len(new_messages))
            for msg in new_messages:
                try:
                    # Skip if already in our list
                    if msg in self._messages:
                        continue

                    if isinstance(msg, AIMessage):
                        content = msg.content if isinstance(msg.content, str) else str(msg.content)
                        if content:
                            if self._current_session:
                                assistant_record = Message.create(
                                    session_id=self._current_session.id,
                                    role=MessageRole.ASSISTANT,
                                    content=content,
                                )
                                self._message_repository.add(assistant_record)
                            self._messages.append(msg)
                            self.message_added.emit(content, False)
                            if not internal_messages_from_result:
                                self._internal_messages.append(msg)
                except Exception as e:
                    logger.warning("Error processing message: %s", e)

        title = result.get("session_title")
        if title and self._current_session:
            title = title.strip()
            if title and self._current_session.title != title:
                self._current_session.title = title
                self._current_session.updated_at = datetime.now()
                self._session_repository.update(self._current_session)
                self.session_updated.emit()

    def _on_graph_error(self, error: str, run_token: str) -> None:
        """Handle graph execution error.

        Args:
            error: The error message
            run_token: The token identifying this execution run
        """
        # Ignore stale errors from cancelled or outdated workers
        if run_token != self._active_run_token:
            return

        self._set_loading(False)
        self.status_changed.emit("Error")
        self.error_occurred.emit(error)

        # Add error message to chat
        self.message_added.emit(f"Error: {error}", False)

    @Slot()
    def cancel_generation(self) -> None:
        """Cancel the current generation (best-effort).

        Note: The worker thread will continue running until completion,
        but results will be ignored due to token invalidation.
        The worker cleanup will happen when it finishes via _cleanup_worker.
        """
        if not self._is_loading:
            return
        self._active_run_token = None  # Invalidate token to ignore stale results
        self._active_session_id = None  # Clear session ID
        self._set_loading(False)
        self.status_changed.emit("Cancelled")
