"""Chat ViewModel for Open Canvas."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from PySide6.QtCore import QObject, Signal, Slot, QThread

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from core.graphs.open_canvas import graph
from core.models import Message, MessageAttachment, MessageRole, Session
from core.config import get_exa_api_key, get_firecrawl_api_key
from core.constants import DEFAULT_EMBEDDING_MODEL
from core.persistence import (
    ArtifactRepository,
    MessageAttachmentRepository,
    MessageRepository,
    SessionRepository,
)
from core.services.docling_service import DoclingService, PdfConversionResult
from core.services.rag_service import RagIndexRequest, RagService
from core.types import (
    ArtifactCollectionV1,
    ArtifactEntry,
    ArtifactExportMeta,
    ArtifactCodeV3,
    ArtifactMarkdownV3,
    ArtifactV3,
)
from ui.viewmodels.settings_viewmodel import SettingsViewModel
from ui.services.image_utils import file_path_to_data_url


class GraphWorker(QThread):
    """Worker thread for running the graph asynchronously."""
    
    finished = Signal(dict)
    error = Signal(str)
    
    def __init__(self, state: dict, config: dict):
        super().__init__()
        self.state = state
        self.config = config
    
    def run(self):
        """Run the graph in the worker thread."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                graph.ainvoke(self.state, self.config)
            )
            
            loop.close()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ChatViewModel(QObject):
    """ViewModel for the chat interface."""

    message_added = Signal(str, bool)
    messages_loaded = Signal(object)
    artifact_changed = Signal()
    is_loading_changed = Signal(bool)
    status_changed = Signal(str)
    error_occurred = Signal(str)
    session_updated = Signal()
    pdf_import_status = Signal(str)  # Emits status updates for PDF import
    pending_attachments_changed = Signal(object)

    def __init__(
        self,
        message_repository: MessageRepository,
        attachment_repository: MessageAttachmentRepository,
        artifact_repository: ArtifactRepository,
        session_repository: SessionRepository,
        settings_viewmodel: SettingsViewModel,
        rag_service: Optional[RagService] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._message_repository = message_repository
        self._attachment_repository = attachment_repository
        self._artifact_repository = artifact_repository
        self._session_repository = session_repository
        self._settings_viewmodel = settings_viewmodel
        self._rag_service = rag_service

        self._messages: list[BaseMessage] = []
        self._internal_messages: list[BaseMessage] = []
        self._artifact: Optional[ArtifactV3] = None
        self._is_loading: bool = False
        self._assistant_id: str = str(uuid4())
        self._current_session: Optional[Session] = None
        self._pending_attachments: list[str] = []

        self._worker: Optional[GraphWorker] = None
        self._cancelled = False

        # PDF import service
        self._docling_service = DoclingService(self)
        self._docling_service.conversion_complete.connect(self._on_pdf_conversion_complete)
        self._pending_pdf_path: Optional[str] = None

        self._settings: dict = {
            "model": "anthropic/claude-3.5-sonnet",
            "temperature": 0.5,
            "max_tokens": 4096,
            "streaming": True,
            "timeout": 120,
        }
    
    @property
    def messages(self) -> list:
        """Get the current message list."""
        return self._messages
    
    @property
    def current_artifact(self) -> Optional[ArtifactV3]:
        """Get the current artifact."""
        return self._artifact
    
    @property
    def is_loading(self) -> bool:
        """Check if currently loading."""
        return self._is_loading

    @property
    def current_session_id(self) -> Optional[str]:
        return self._current_session.id if self._current_session else None

    @property
    def pending_attachments(self) -> list[str]:
        return self._pending_attachments.copy()

    def add_pending_attachment(self, file_path: str) -> None:
        if not self._current_session:
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
        if not self._pending_attachments:
            return
        self._pending_attachments = []
        self.pending_attachments_changed.emit([])
    
    def _set_loading(self, loading: bool):
        """Set loading state."""
        self._is_loading = loading
        self.is_loading_changed.emit(loading)

    def load_session(self, session_id: str) -> None:
        session = self._session_repository.get_by_id(session_id)
        if session is None:
            return
        self._clear_pending_attachments()
        self._current_session = session
        stored_messages = self._message_repository.get_by_session(session_id)
        self._messages = []
        for message in stored_messages:
            if message.role == MessageRole.USER:
                self._messages.append(HumanMessage(content=message.content))
            elif message.role == MessageRole.ASSISTANT:
                self._messages.append(AIMessage(content=message.content))
        self._internal_messages = self._messages.copy()
        self._artifact = self._artifact_repository.get_for_session(session_id)
        self.messages_loaded.emit(
            [
                {"content": msg.content, "is_user": isinstance(msg, HumanMessage)}
                for msg in self._messages
            ]
        )
        self.artifact_changed.emit()

    def clear(self) -> None:
        self._messages = []
        self._internal_messages = []
        self._artifact = None
        self._current_session = None
        self._clear_pending_attachments()
        self.messages_loaded.emit([])
        self.artifact_changed.emit()
    
    @Slot(str)
    def send_message(self, content: str):
        """
        Send a user message and run the graph.
        
        Args:
            content: The user's message content
        """
        if self._is_loading or not self._current_session:
            return

        self._cancelled = False

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
        self._clear_pending_attachments()

        # Start loading
        self._set_loading(True)
        self.status_changed.emit("Processing...")
        
        # Prepare state
        internal_messages = (
            self._internal_messages.copy()
            if self._internal_messages
            else self._messages.copy()
        )
        state = {
            "messages": self._messages.copy(),
            "internal_messages": internal_messages,
            "web_search_enabled": self._settings_viewmodel.deep_search_enabled,
        }
        
        if self._artifact:
            state["artifact"] = self._artifact
        
        exa_api_key = self._settings_viewmodel.exa_api_key or get_exa_api_key()
        firecrawl_api_key = (
            self._settings_viewmodel.firecrawl_api_key or get_firecrawl_api_key()
        )

        config = {
            "configurable": {
                "assistant_id": self._assistant_id,
                "model": self._settings_viewmodel.default_model
                or self._settings.get("model", "anthropic/claude-3.5-sonnet"),
                "temperature": self._settings.get("temperature", 0.5),
                "max_tokens": self._settings.get("max_tokens", 4096),
                "api_key": self._settings_viewmodel.api_key or None,
                "session_id": self._current_session.id,
                "workspace_id": self._current_session.workspace_id,
                "rag_enabled": self._settings_viewmodel.rag_enabled,
                "rag_scope": self._settings_viewmodel.rag_scope,
                "rag_k_lex": self._settings_viewmodel.rag_k_lex,
                "rag_k_vec": self._settings_viewmodel.rag_k_vec,
                "rag_rrf_k": self._settings_viewmodel.rag_rrf_k,
                "rag_max_candidates": self._settings_viewmodel.rag_max_candidates,
                "rag_embedding_model": self._settings_viewmodel.rag_embedding_model,
                "rag_enable_query_rewrite": self._settings_viewmodel.rag_enable_query_rewrite,
                "rag_enable_llm_rerank": self._settings_viewmodel.rag_enable_llm_rerank,
                "web_search_provider": self._settings_viewmodel.search_provider,
                "web_search_num_results": self._settings_viewmodel.deep_search_num_results,
                "exa_api_key": exa_api_key or None,
                "firecrawl_api_key": firecrawl_api_key or None,
            }
        }
        
        # Run in worker thread
        self._worker = GraphWorker(state, config)
        self._worker.finished.connect(self._on_graph_finished)
        self._worker.error.connect(self._on_graph_error)
        self._worker.start()
    
    def _on_graph_finished(self, result: dict):
        """Handle successful graph execution."""
        if self._cancelled:
            self._cancelled = False
            self._set_loading(False)
            return

        self._set_loading(False)
        self.status_changed.emit("Ready")
        
        # Debug: Print result keys
        print(f"[DEBUG] Graph result keys: {list(result.keys())}")

        internal_messages_from_result = False
        if "internal_messages" in result and result["internal_messages"] is not None:
            self._internal_messages = list(result["internal_messages"])
            internal_messages_from_result = True
        
        # Update artifact first
        if "artifact" in result and result["artifact"]:
            print(f"[DEBUG] Artifact found in result: {type(result['artifact'])}")
            self._artifact = result["artifact"]
            if self._current_session:
                self._artifact_repository.save_for_session(
                    self._current_session.id,
                    self._artifact,
                )
            self.artifact_changed.emit()
            self._index_active_text_artifact()
            print(f"[DEBUG] Artifact emitted with {len(self._artifact.contents)} contents")
        else:
            print(f"[DEBUG] No artifact in result. 'artifact' key exists: {'artifact' in result}")
        
        # Update messages with error handling
        if "messages" in result:
            new_messages = result["messages"]
            print(f"[DEBUG] Messages in result: {len(new_messages)}")
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
                    print(f"[DEBUG] Error processing message: {e}")

        title = result.get("session_title")
        if title and self._current_session:
            title = title.strip()
            if title and self._current_session.title != title:
                self._current_session.title = title
                self._current_session.updated_at = datetime.now()
                self._session_repository.update(self._current_session)
                self.session_updated.emit()
    
    def _on_graph_error(self, error: str):
        """Handle graph execution error."""
        self._set_loading(False)
        self.status_changed.emit("Error")
        self.error_occurred.emit(error)
        
        # Add error message to chat
        self.message_added.emit(f"Error: {error}", False)
    
    @Slot()
    def prev_artifact_version(self):
        """Navigate to previous artifact version."""
        if not self._artifact:
            return
        
        if self._artifact.current_index > 1:
            self._artifact.current_index -= 1
            self.artifact_changed.emit()
    
    @Slot()
    def next_artifact_version(self):
        """Navigate to next artifact version."""
        if not self._artifact:
            return
        
        if self._artifact.current_index < len(self._artifact.contents):
            self._artifact.current_index += 1
            self.artifact_changed.emit()
    
    @Slot()
    def clear_conversation(self):
        """Clear the conversation history (UI-only)."""
        self.clear()

    @Slot()
    def cancel_generation(self):
        """Cancel the current generation (best-effort)."""
        if not self._is_loading:
            return
        self._cancelled = True
        self._set_loading(False)
        self.status_changed.emit("Cancelled")

    # ---- PDF Import Methods ----

    @Slot(str)
    def import_pdf(self, pdf_path: str) -> None:
        """Start importing a PDF file as a new text artifact.

        Args:
            pdf_path: Absolute path to the PDF file.
        """
        if not self._current_session:
            self.error_occurred.emit("No active session for PDF import")
            return
        if self._docling_service.is_busy():
            self.error_occurred.emit("A PDF conversion is already in progress")
            return

        self.pdf_import_status.emit(f"Converting PDF: {pdf_path}")
        self._pending_pdf_path = pdf_path
        self._docling_service.convert_pdf(pdf_path)

    def _on_pdf_conversion_complete(self, result: PdfConversionResult) -> None:
        """Handle completed PDF conversion and create artifact.

        Args:
            result: Conversion result from DoclingService.
        """
        if not result.success:
            self.error_occurred.emit(result.error_message)
            self.pdf_import_status.emit("")
            return

        if not self._current_session:
            self.error_occurred.emit("No active session")
            self.pdf_import_status.emit("")
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
        collection = self._artifact_repository.get_collection(self._current_session.id)
        if collection is None:
            collection = ArtifactCollectionV1(
                version=1,
                artifacts=[entry],
                active_artifact_id=entry.id,
            )
        else:
            collection.artifacts.append(entry)
            collection.active_artifact_id = entry.id

        self._artifact_repository.save_collection(self._current_session.id, collection)

        # Update current artifact reference and emit signal
        self._artifact = new_artifact
        self.artifact_changed.emit()
        self.pdf_import_status.emit(f"Imported: {result.source_filename}")

        self._index_pdf_artifact(
            entry_id=entry.id,
            source_name=result.source_filename,
            content=result.markdown,
            source_path=self._pending_pdf_path,
        )
        self._pending_pdf_path = None

    def _index_pdf_artifact(
        self,
        entry_id: str,
        source_name: str,
        content: str,
        source_path: Optional[str],
    ) -> None:
        if not self._current_session or not self._rag_service:
            return
        request = RagIndexRequest(
            workspace_id=self._current_session.workspace_id,
            session_id=self._current_session.id,
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

    def _index_active_text_artifact(self) -> None:
        if not self._current_session or not self._rag_service:
            return
        if not self._settings_viewmodel.rag_index_text_artifacts:
            return
        collection = self._artifact_repository.get_collection(self._current_session.id)
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
            workspace_id=self._current_session.workspace_id,
            session_id=self._current_session.id,
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
