"""Chat ViewModel for managing chat conversations with agent support."""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import uuid

from PySide6.QtCore import QObject, Signal, Property, Slot
from PySide6.QtGui import QImage
from typing import Dict

from ..core.models import Message, MessageRole, Chat, Agent, AgentMemory, MessageAttachment
from ..core.agents import AgentRepository, MemoryCommandParser
from ..persistence import (
    MessageRepository,
    ChatRepository,
    AgentMemoryRepository,
    WorkspaceMemoryRepository,
    AttachmentRepository,
    Database,
    SettingsRepository,
)
from ..infrastructure.langchain_service import LangChainService
from ..infrastructure.memory_aggregation_service import MemoryAggregationService
from ..infrastructure.rag_service import RagService
from ..infrastructure import image_utils

logger = logging.getLogger(__name__)


class ChatViewModel(QObject):
    """ViewModel for chat conversation management with agent support."""
    
    messages_changed = Signal()
    is_loading_changed = Signal()
    current_chat_changed = Signal()
    streaming_content_changed = Signal()
    error_occurred = Signal(str)
    
    # Agent-related signals
    current_agent_changed = Signal()
    available_agents_changed = Signal()
    
    # RAG-related signals
    rag_active_changed = Signal(bool)
    
    # Attachment-related signals
    pending_attachments_changed = Signal()
    
    # Paging-related signals
    history_loading_changed = Signal()
    messages_prepended = Signal(int)  # Emits count of prepended messages
    
    def __init__(
        self,
        message_repository: MessageRepository,
        chat_repository: ChatRepository,
        agent_repository: AgentRepository,
        agent_memory_repository: AgentMemoryRepository,
        workspace_memory_repository: WorkspaceMemoryRepository,
        langchain_service: LangChainService,
        settings_repository: Optional[SettingsRepository] = None,
        memory_aggregation_service: Optional[MemoryAggregationService] = None,
        rag_service: Optional[RagService] = None,
        attachment_repository: Optional[AttachmentRepository] = None,
        settings_viewmodel=None,
        parent: Optional[QObject] = None,
    ):
        """Initialize the ChatViewModel.
        
        Args:
            message_repository: Repository for message persistence.
            chat_repository: Repository for chat persistence.
            agent_repository: Repository for agent configurations.
            agent_memory_repository: Repository for agent memories.
            workspace_memory_repository: Repository for workspace memories.
            langchain_service: Service for LangChain-based chat.
            settings_repository: Repository for settings (optional).
            memory_aggregation_service: Aggregation service for summarization (optional).
            rag_service: RAG service for knowledge retrieval (optional).
            parent: Parent QObject.
        """
        super().__init__(parent)
        self._message_repository = message_repository
        self._chat_repository = chat_repository
        self._agent_repository = agent_repository
        self._agent_memory_repository = agent_memory_repository
        self._workspace_memory_repository = workspace_memory_repository
        self._langchain_service = langchain_service
        self._settings_repository = settings_repository or SettingsRepository(
            Database()
        )
        self._memory_aggregation_service = memory_aggregation_service
        self._rag_service = rag_service
        self._attachment_repository = attachment_repository
        self._settings_viewmodel = settings_viewmodel
        
        self._messages: List[Message] = []
        self._current_chat: Optional[Chat] = None
        self._is_loading = False
        self._streaming_content = ""
        
        # Agent state
        self._current_agent: Optional[Agent] = None
        self._available_agents: List[Agent] = []
        
        # RAG state
        self._rag_active = False
        
        # Pending attachments (QImages not yet sent)
        self._pending_attachments: List[QImage] = []
        
        # Message attachments cache (message_id -> list of QImages)
        # This is in-memory only for the current session
        self._message_attachments: Dict[str, List[QImage]] = {}
        
        # Paging state
        self._has_more_history = False
        self._is_loading_history = False
        self._oldest_loaded_timestamp: Optional[datetime] = None
        
        # Load agents and set default
        self._refresh_agents()
        
        # Connect LangChain service signals
        self._langchain_service.response_chunk.connect(self._on_response_chunk)
        self._langchain_service.response_completed.connect(self._on_response_completed)
        self._langchain_service.response_error.connect(self._on_response_error)
    
    def _refresh_agents(self) -> None:
        """Refresh the list of available agents."""
        self._available_agents = self._agent_repository.get_all()
        
        # Set default agent if not already set
        if self._current_agent is None:
            self._current_agent = self._agent_repository.get_default()
        
        self.available_agents_changed.emit()
    
    @Property(list, notify=messages_changed)
    def messages(self) -> List[Message]:
        """Get the current messages."""
        return self._messages
    
    @Property(bool, notify=is_loading_changed)
    def is_loading(self) -> bool:
        """Check if a response is being generated."""
        return self._is_loading
    
    @Property(str, notify=streaming_content_changed)
    def streaming_content(self) -> str:
        """Get the current streaming content."""
        return self._streaming_content
    
    @Property(object, notify=current_chat_changed)
    def current_chat(self) -> Optional[Chat]:
        """Get the current chat."""
        return self._current_chat
    
    @Property(object, notify=current_agent_changed)
    def current_agent(self) -> Optional[Agent]:
        """Get the current agent."""
        return self._current_agent
    
    @Property(list, notify=available_agents_changed)
    def available_agents(self) -> List[Agent]:
        """Get the list of available agents."""
        return self._available_agents
    
    @Property(bool, notify=rag_active_changed)
    def rag_active(self) -> bool:
        """Check if RAG is active."""
        return self._rag_active
    
    @Slot(bool)
    def set_rag_active(self, active: bool) -> None:
        """Set RAG active state.
        
        Args:
            active: Whether RAG should be active.
        """
        if self._rag_active != active:
            self._rag_active = active
            self.rag_active_changed.emit(active)
    
    @property
    def pending_attachments(self) -> List[QImage]:
        """Get the list of pending attachments."""
        return self._pending_attachments.copy()
    
    @property
    def is_multimodal(self) -> bool:
        """Check if the current model supports multimodal inputs."""
        if self._settings_viewmodel is None:
            return False
        model_id = self._settings_viewmodel.default_model
        return self._settings_viewmodel.is_model_multimodal(model_id)
    
    @property
    def can_capture(self) -> bool:
        """Check if screen capture is allowed (model is multimodal)."""
        return self.is_multimodal
    
    @Slot(QImage)
    def add_pending_attachment(self, image: QImage) -> None:
        """Add an image to the pending attachments list.
        
        Args:
            image: The QImage to add.
        """
        if not image.isNull():
            self._pending_attachments.append(image.copy())
            self.pending_attachments_changed.emit()
    
    @Slot(int)
    def remove_pending_attachment(self, index: int) -> None:
        """Remove a pending attachment by index.
        
        Args:
            index: The index of the attachment to remove.
        """
        if 0 <= index < len(self._pending_attachments):
            del self._pending_attachments[index]
            self.pending_attachments_changed.emit()
    
    @Slot()
    def clear_pending_attachments(self) -> None:
        """Clear all pending attachments."""
        if self._pending_attachments:
            self._pending_attachments.clear()
            self.pending_attachments_changed.emit()
    
    def get_message_attachments(self, message_id: str) -> List[QImage]:
        """Get attachments for a specific message.
        
        Args:
            message_id: The message ID to get attachments for.
            
        Returns:
            List of QImage attachments for this message.
        """
        return self._message_attachments.get(message_id, [])
    
    @Slot(str)
    def select_agent(self, agent_id: str) -> None:
        """Select an agent by ID.
        
        Args:
            agent_id: The agent's unique identifier.
        """
        agent = self._agent_repository.get_by_id(agent_id)
        if agent is not None:
            self._current_agent = agent
            self.current_agent_changed.emit()
    
    @Slot()
    def reload_agents(self) -> None:
        """Reload agents from configuration files."""
        self._agent_repository.reload()
        self._refresh_agents()
    
    @Slot(str)
    def load_chat(self, chat_id: str) -> None:
        """Load a chat by ID.
        
        Args:
            chat_id: The ID of the chat to load.
        """
        chat = self._chat_repository.get_by_id(chat_id)
        if chat is None:
            return
        
        self._current_chat = chat
        
        # Use paged loading for initial chat load
        messages, has_more = self._message_repository.get_recent_page(chat_id)
        self._messages = messages
        self._has_more_history = has_more
        self._oldest_loaded_timestamp = messages[0].timestamp if messages else None
        
        self._streaming_content = ""
        self.current_chat_changed.emit()
        self.messages_changed.emit()
    
    @Property(bool, notify=history_loading_changed)
    def has_more_history(self) -> bool:
        """Check if there are more older messages to load."""
        return self._has_more_history
    
    @Property(bool, notify=history_loading_changed)
    def is_loading_history(self) -> bool:
        """Check if history is currently being loaded."""
        return self._is_loading_history
    
    @Slot()
    def load_older_messages(self) -> None:
        """Load older messages from history.
        
        Fetches the next page of older messages and prepends them to the
        message list. Emits messages_prepended with the count of new messages.
        """
        if (
            self._current_chat is None
            or not self._has_more_history
            or self._is_loading_history
            or self._oldest_loaded_timestamp is None
        ):
            return
        
        self._is_loading_history = True
        self.history_loading_changed.emit()
        
        try:
            older_messages, has_more = self._message_repository.get_older_page(
                self._current_chat.id,
                self._oldest_loaded_timestamp,
            )
            
            if older_messages:
                # Prepend older messages
                self._messages = older_messages + self._messages
                self._oldest_loaded_timestamp = older_messages[0].timestamp
                self._has_more_history = has_more
                self.messages_prepended.emit(len(older_messages))
            else:
                self._has_more_history = False
        finally:
            self._is_loading_history = False
            self.history_loading_changed.emit()
    
    @Slot(str)
    def send_message(self, content: str) -> None:
        """Send a user message and get a response.
        
        Args:
            content: The message content.
        """
        if not content.strip() or self._current_chat is None:
            return
        
        if self._is_loading:
            return
        
        if self._current_agent is None:
            self.error_occurred.emit("No agent selected. Please select an agent.")
            return
        
        # Check if service is configured
        if not self._langchain_service.is_configured():
            self.error_occurred.emit(
                "Please configure your OpenRouter API key in Settings -> Models."
            )
            return
        
        # Check for attachments with non-multimodal model
        if self._pending_attachments and not self.is_multimodal:
            self.error_occurred.emit(
                "The current model does not support image attachments. "
                "Please select a multimodal model or remove the attachments."
            )
            return
        
        # Parse @RAG command first (before memory commands strip it)
        rag_cmd = MemoryCommandParser.extract_rag_command(content)
        if rag_cmd is not None:
            if rag_cmd.action == "on":
                self._rag_active = True
            elif rag_cmd.action == "off":
                self._rag_active = False
            else:  # toggle
                self._rag_active = not self._rag_active
            self.rag_active_changed.emit(self._rag_active)
        
        # Parse memory commands (this also strips @RAG commands)
        cleaned_content, commands = MemoryCommandParser.parse(content)
        
        # Process memory commands
        for cmd in commands:
            if cmd.command_type == "remember":
                memory = AgentMemory.create(
                    agent_id=self._current_agent.id,
                    content=cmd.content,
                )
                self._agent_memory_repository.add(memory)
                if self._memory_aggregation_service and self._current_chat is not None:
                    self._memory_aggregation_service.link_agent_memory(
                        self._current_chat.workspace_id,
                        memory,
                    )
            elif cmd.command_type == "forget":
                self._agent_memory_repository.delete_matching(
                    agent_id=self._current_agent.id,
                    phrase=cmd.content,
                )
        
        # If only commands (no actual message), don't send to LLM
        if not cleaned_content:
            feedback_parts = []
            if commands:
                feedback_parts.append("Memory commands processed.")
            if rag_cmd is not None:
                status = "enabled" if self._rag_active else "disabled"
                feedback_parts.append(f"RAG {status}.")
            
            if feedback_parts:
                feedback_msg = Message.create(
                    chat_id=self._current_chat.id,
                    role=MessageRole.ASSISTANT,
                    content=" ".join(feedback_parts),
                )
                self._message_repository.add(feedback_msg)
                self._messages.append(feedback_msg)
                self.messages_changed.emit()
            return
        
        # Create and save user message (with cleaned content)
        user_message = Message.create(
            chat_id=self._current_chat.id,
            role=MessageRole.USER,
            content=cleaned_content,
        )
        self._message_repository.add(user_message)
        self._messages.append(user_message)
        
        # Store pending attachments with this message for display
        if self._pending_attachments:
            self._message_attachments[user_message.id] = [img.copy() for img in self._pending_attachments]
        
        self.messages_changed.emit()
        
        # Update chat title if it's the first message
        if len(self._messages) == 1:
            self._current_chat.title = cleaned_content[:50]
            self._current_chat.updated_at = datetime.now()
            self._chat_repository.update(self._current_chat)
            self.current_chat_changed.emit()
        
        # Start loading
        self._is_loading = True
        self._streaming_content = ""
        self.is_loading_changed.emit()
        
        # Get agent memories
        memories = self._agent_memory_repository.get_by_agent(self._current_agent.id)

        # Decide on workspace_memories vs rag_context (mutually exclusive per design)
        workspace_memories: Optional[str] = None
        rag_context: Optional[str] = None
        
        if self._rag_active and self._rag_service is not None and self._rag_service.is_ready:
            # RAG is active - query the index and build context
            try:
                results = self._rag_service.query_sync(cleaned_content)
                if results:
                    # Build RAG context from results with citations
                    context_parts = []
                    for i, result in enumerate(results, 1):
                        citation = result.citation
                        context_parts.append(f"[{i}] {result.content}\n--- Source: {citation}")
                    rag_context = "\n\n".join(context_parts)
                    logger.debug(f"RAG query returned {len(results)} results")
            except Exception as e:
                logger.warning(f"RAG query failed: {e}")
                # Continue without RAG context
        else:
            # RAG is not active - use workspace memories
            if self._current_chat is not None:
                max_tokens = self._settings_repository.get_max_workspace_memory_tokens()
                workspace_memories = self._workspace_memory_repository.get_aggregated_content(
                    self._current_chat.workspace_id,
                    max_tokens=max_tokens,
                )
                if not workspace_memories:
                    workspace_memories = None
        
        # Convert pending attachments to base64 data URIs
        image_data_uris = []
        if self._pending_attachments:
            for img in self._pending_attachments:
                resized = image_utils.resize_image(img, max_side=1280)
                data_uri = image_utils.image_to_base64(resized, "PNG")
                image_data_uris.append(data_uri)
            # Clear pending attachments after preparing them
            self._pending_attachments.clear()
            self.pending_attachments_changed.emit()
        
        # Send to LangChain service with agent, memories, context, and images
        self._langchain_service.send_message(
            agent=self._current_agent,
            memories=memories,
            workspace_memories=workspace_memories,
            rag_context=rag_context,
            messages=self._messages,
            image_data_uris=image_data_uris if image_data_uris else None,
        )
    
    @Slot()
    def cancel_generation(self) -> None:
        """Cancel the current generation."""
        if self._is_loading:
            self._langchain_service.cancel()
            self._is_loading = False
            self.is_loading_changed.emit()
    
    def _on_response_chunk(self, chunk: str) -> None:
        """Handle a response chunk from the LLM."""
        self._streaming_content += chunk
        self.streaming_content_changed.emit()
    
    def _on_response_completed(self, response: str) -> None:
        """Handle completion of the LLM response."""
        if self._current_chat is None:
            return
        
        # Create and save assistant message
        assistant_message = Message.create(
            chat_id=self._current_chat.id,
            role=MessageRole.ASSISTANT,
            content=response,
        )
        self._message_repository.add(assistant_message)
        self._messages.append(assistant_message)
        
        # Update chat timestamp
        self._current_chat.updated_at = datetime.now()
        self._chat_repository.update(self._current_chat)
        
        self._is_loading = False
        self._streaming_content = ""
        self.messages_changed.emit()
        self.is_loading_changed.emit()
        self.streaming_content_changed.emit()

        if (
            self._memory_aggregation_service is not None
            and self._current_chat is not None
            and self._settings_repository.get_auto_summarize()
        ):
            self._memory_aggregation_service.summarize_chat(self._current_chat.id)
    
    def _on_response_error(self, error: str) -> None:
        """Handle an error from the LLM."""
        self._is_loading = False
        self._streaming_content = ""
        self.is_loading_changed.emit()
        self.streaming_content_changed.emit()
        self.error_occurred.emit(f"LLM Error: {error}")
    
    def clear(self) -> None:
        """Clear the current chat state."""
        self._messages = []
        self._current_chat = None
        self._streaming_content = ""
        self._is_loading = False
        self.messages_changed.emit()
        self.current_chat_changed.emit()
