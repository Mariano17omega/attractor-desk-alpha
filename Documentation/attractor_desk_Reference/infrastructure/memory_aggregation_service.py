"""Service for aggregating workspace memories."""

import asyncio
from difflib import SequenceMatcher
from typing import Optional

from PySide6.QtCore import QObject, Signal, QThread

from ..core.models import AgentMemory, WorkspaceMemory, MemorySourceType, MessageRole
from ..persistence import WorkspaceMemoryRepository, MessageRepository, ChatRepository
from .langchain_service import LangChainService
from .openrouter_client import OpenRouterClient, ChatMessage, OpenRouterConfig


SUMMARY_PROMPT = (
    "You are a research assistant. Summarize the key points from the following "
    "conversation in 2-3 concise bullet points. Focus on:\n"
    "- Main topics discussed\n"
    "- Decisions made or conclusions reached\n"
    "- Important facts or references mentioned\n\n"
    "Conversation:\n{conversation}\n\nSummary:"
)


class SummarizationWorker(QThread):
    """Worker thread for LLM-based summarization."""

    completed = Signal(str)
    error = Signal(str)

    def __init__(
        self,
        config: OpenRouterConfig,
        prompt: str,
        conversation: str,
        parent: Optional[QObject] = None,
    ):
        """Initialize the worker."""
        super().__init__(parent)
        self._config = config
        self._prompt = prompt
        self._conversation = conversation

    def run(self) -> None:
        """Execute summarization in a background thread."""

        async def _run() -> None:
            client = OpenRouterClient(self._config)
            try:
                messages = [
                    ChatMessage(role="system", content=self._prompt),
                    ChatMessage(role="user", content=self._conversation),
                ]
                summary = ""
                async for chunk in client.chat_completion(messages, stream=False):
                    summary += chunk
                self.completed.emit(summary.strip())
            except Exception as exc:
                self.error.emit(str(exc))
            finally:
                await client.close()

        asyncio.run(_run())


class MemoryAggregationService(QObject):
    """Service for aggregating and summarizing workspace memories."""

    summarization_started = Signal(str, str)  # workspace_id, chat_id
    summarization_completed = Signal(str, str)  # workspace_id, summary
    summarization_error = Signal(str)  # error message

    def __init__(
        self,
        workspace_memory_repo: WorkspaceMemoryRepository,
        message_repo: MessageRepository,
        chat_repo: ChatRepository,
        langchain_service: LangChainService,
        parent: Optional[QObject] = None,
    ):
        """Initialize the aggregation service."""
        super().__init__(parent)
        self._workspace_memory_repo = workspace_memory_repo
        self._message_repo = message_repo
        self._chat_repo = chat_repo
        self._langchain_service = langchain_service
        self._worker: Optional[SummarizationWorker] = None

    def summarize_chat(self, chat_id: str) -> None:
        """Summarize a chat conversation and add to workspace memories."""
        chat = self._chat_repo.get_by_id(chat_id)
        if chat is None:
            self.summarization_error.emit("Chat not found for summarization.")
            return

        if not self._langchain_service.is_configured():
            self.summarization_error.emit(
                "OpenRouter is not configured for summarization."
            )
            return

        messages = self._message_repo.get_by_chat(chat_id)
        if not messages:
            self.summarization_error.emit("No messages found to summarize.")
            return

        conversation_lines = []
        for msg in messages:
            role_label = msg.role.value.upper()
            if msg.role == MessageRole.ASSISTANT:
                role_label = "ASSISTANT"
            elif msg.role == MessageRole.USER:
                role_label = "USER"
            elif msg.role == MessageRole.SYSTEM:
                role_label = "SYSTEM"
            conversation_lines.append(f"{role_label}: {msg.content}")
        conversation = "\n".join(conversation_lines)

        prompt = SUMMARY_PROMPT.format(conversation=conversation)
        config = self._langchain_service.config

        self.summarization_started.emit(chat.workspace_id, chat.id)
        self._worker = SummarizationWorker(
            config=config,
            prompt=prompt,
            conversation=conversation,
            parent=self,
        )
        self._worker.completed.connect(
            lambda summary: self._on_summary_ready(chat.workspace_id, chat.id, summary)
        )
        self._worker.error.connect(self._on_summary_error)
        self._worker.start()

    def _on_summary_ready(self, workspace_id: str, chat_id: str, summary: str) -> None:
        """Handle completed summarization."""
        self._worker = None
        if not summary.strip():
            self.summarization_error.emit("Summarization returned empty content.")
            return

        self._workspace_memory_repo.delete_by_source(workspace_id, chat_id)
        memory = WorkspaceMemory.create(
            workspace_id=workspace_id,
            content=summary.strip(),
            source_type=MemorySourceType.CHAT_SUMMARY,
            source_id=chat_id,
        )
        self._workspace_memory_repo.add(memory)
        self.summarization_completed.emit(workspace_id, summary.strip())

    def _on_summary_error(self, message: str) -> None:
        """Handle summarization error."""
        self._worker = None
        self.summarization_error.emit(message)

    def link_agent_memory(self, workspace_id: str, agent_memory: AgentMemory) -> None:
        """Link an agent memory to a workspace for cross-reference."""
        memory = WorkspaceMemory.create(
            workspace_id=workspace_id,
            content=agent_memory.content,
            source_type=MemorySourceType.AGENT_MEMORY,
            source_id=agent_memory.id,
        )
        self._workspace_memory_repo.add(memory)

    def deduplicate_memories(
        self, workspace_id: str, similarity_threshold: float = 0.85
    ) -> int:
        """Remove duplicate memories based on text similarity."""
        memories = self._workspace_memory_repo.get_by_workspace(workspace_id)
        kept: list[WorkspaceMemory] = []
        removed = 0

        for memory in memories:
            if not memory.content.strip():
                continue
            if self._is_duplicate(memory, kept, similarity_threshold):
                self._workspace_memory_repo.delete(memory.id)
                removed += 1
            else:
                kept.append(memory)

        return removed

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (word-count heuristic)."""
        words = text.split()
        return max(1, len(words))

    def _is_duplicate(
        self,
        memory: WorkspaceMemory,
        existing: list[WorkspaceMemory],
        similarity_threshold: float,
    ) -> bool:
        """Check if a memory duplicates existing ones."""
        for candidate in existing:
            similarity = SequenceMatcher(
                None, memory.content.strip(), candidate.content.strip()
            ).ratio()
            if similarity >= similarity_threshold:
                return True
        return False
