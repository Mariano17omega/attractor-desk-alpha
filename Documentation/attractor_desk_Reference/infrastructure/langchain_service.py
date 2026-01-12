"""LangChain-based service for agent chat execution with memory injection."""

import asyncio
import logging
from typing import AsyncIterator, Callable, List, Optional

from PySide6.QtCore import QObject, Signal, QThread

from ..core.models import Agent, AgentMemory, Message, MessageRole
from .openrouter_client import OpenRouterConfig, ChatMessage

logger = logging.getLogger(__name__)


def build_system_prompt(
    agent: Agent,
    memories: List[AgentMemory],
    workspace_memories: Optional[str] = None,
    rag_context: Optional[str] = None,
) -> str:
    """Build the full system prompt with agent config and memories.
    
    Args:
        agent: The agent configuration.
        memories: List of agent memories to inject.
        workspace_memories: Pre-formatted workspace memory string to inject.
        rag_context: Pre-formatted RAG context snippets to inject.
        
    Returns:
        Complete system prompt string.
    """
    parts = [agent.system_prompt.strip()]
    
    if memories:
        memory_section = "\n\n## Long-term Memories\n"
        memory_section += "The following are things you should remember about this user:\n"
        for memory in memories:
            memory_section += f"- {memory.content}\n"
        parts.append(memory_section)

    if workspace_memories:
        workspace_section = "\n\n## Workspace Context\n"
        workspace_section += (
            "The following are persistent notes about this research workspace:\n"
        )
        workspace_section += workspace_memories.strip()
        parts.append(workspace_section)
    
    if rag_context:
        rag_section = "\n\n## RAG Context\n"
        rag_section += (
            "The following are relevant snippets retrieved from the knowledge base:\n"
        )
        rag_section += rag_context.strip()
        parts.append(rag_section)
    
    return "\n".join(parts)


class LangChainWorker(QThread):
    """Worker thread for LangChain-based chat completion."""
    
    chunk_received = Signal(str)
    completed = Signal(str)
    error = Signal(str)
    
    def __init__(
        self,
        config: OpenRouterConfig,
        agent: Agent,
        memories: List[AgentMemory],
        workspace_memories: Optional[str],
        rag_context: Optional[str],
        messages: List[Message],
        image_data_uris: Optional[List[str]] = None,
        parent: Optional[QObject] = None,
    ):
        """Initialize the worker.
        
        Args:
            config: OpenRouter configuration.
            agent: The agent to use for the request.
            memories: Agent memories to inject.
            workspace_memories: Workspace memories to inject.
            rag_context: RAG context snippets to inject.
            messages: Chat messages to send.
            image_data_uris: Optional list of base64 data URIs for image attachments.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self.config = config
        self.agent = agent
        self.memories = memories
        self.workspace_memories = workspace_memories
        self.rag_context = rag_context
        self.messages = messages
        self.image_data_uris = image_data_uris or []
        self._cancelled = False
    
    def cancel(self) -> None:
        """Cancel the current request."""
        self._cancelled = True
    
    def run(self) -> None:
        """Execute the LangChain request in a separate thread."""
        async def _run_langchain() -> None:
            try:
                # Try to use LangChain if available
                from langchain_openai import ChatOpenAI
                from langchain_core.messages import (
                    HumanMessage,
                    AIMessage,
                    SystemMessage,
                )
                
                # Configure LangChain to use OpenRouter
                llm = ChatOpenAI(
                    model=self.config.model,
                    openai_api_key=self.config.api_key,
                    openai_api_base=self.config.base_url,
                    streaming=True,
                    default_headers={
                        "HTTP-Referer": "https://attractor-desk.app",
                        "X-Title": "Attractor Desk",
                    },
                )
                
                # Build messages with system prompt
                system_prompt = build_system_prompt(
                    self.agent, self.memories, self.workspace_memories, self.rag_context
                )
                lc_messages = [SystemMessage(content=system_prompt)]
                
                for msg in self.messages:
                    if msg.role == MessageRole.USER:
                        lc_messages.append(HumanMessage(content=msg.content))
                    elif msg.role == MessageRole.ASSISTANT:
                        lc_messages.append(AIMessage(content=msg.content))
                
                # If we have images, add them to the last user message as multi-part content
                if self.image_data_uris and lc_messages:
                    # Find last human message and replace with multi-part
                    for i in range(len(lc_messages) - 1, -1, -1):
                        if isinstance(lc_messages[i], HumanMessage):
                            text_content = lc_messages[i].content
                            # Build multi-part content
                            content_parts = [{"type": "text", "text": text_content}]
                            for data_uri in self.image_data_uris:
                                content_parts.append({
                                    "type": "image_url",
                                    "image_url": {"url": data_uri}
                                })
                            lc_messages[i] = HumanMessage(content=content_parts)
                            break
                
                # Stream the response
                full_response = ""
                async for chunk in llm.astream(lc_messages):
                    if self._cancelled:
                        break
                    content = chunk.content
                    if content:
                        full_response += content
                        self.chunk_received.emit(content)
                
                if not self._cancelled:
                    self.completed.emit(full_response)
                    
            except ImportError:
                # Fall back to direct OpenRouter client
                await self._fallback_openrouter()
            except Exception as e:
                logger.exception("LangChain error")
                self.error.emit(str(e))
        
        async def _run() -> None:
            try:
                await _run_langchain()
            except Exception as e:
                # Final fallback to simple OpenRouter
                try:
                    await self._fallback_openrouter()
                except Exception as fallback_error:
                    self.error.emit(str(fallback_error))
        
        asyncio.run(_run())
    
    async def _fallback_openrouter(self) -> None:
        """Fallback to direct OpenRouter API when LangChain unavailable."""
        from .openrouter_client import OpenRouterClient
        
        # Build system prompt
        system_prompt = build_system_prompt(
            self.agent, self.memories, self.workspace_memories, self.rag_context
        )
        
        # Create message list with system prompt
        chat_messages = [ChatMessage(role="system", content=system_prompt)]
        for msg in self.messages:
            chat_messages.append(ChatMessage(role=msg.role.value, content=msg.content))
        
        # Add images to last user message for fallback (OpenRouter supports multi-part content)
        if self.image_data_uris and chat_messages:
            for i in range(len(chat_messages) - 1, -1, -1):
                if chat_messages[i].role == "user":
                    text_content = chat_messages[i].content
                    content_parts = [{"type": "text", "text": text_content}]
                    for data_uri in self.image_data_uris:
                        content_parts.append({
                            "type": "image_url",
                            "image_url": {"url": data_uri}
                        })
                    chat_messages[i] = ChatMessage(role="user", content=content_parts)
                    break
        
        # Use global model from config
        config = self.config
        
        client = OpenRouterClient(config)
        full_response = ""
        
        try:
            async for chunk in client.chat_completion(chat_messages):
                if self._cancelled:
                    break
                full_response += chunk
                self.chunk_received.emit(chunk)
            
            if not self._cancelled:
                self.completed.emit(full_response)
        finally:
            await client.close()


class LangChainService(QObject):
    """Service for LangChain-based agent chat execution."""
    
    response_chunk = Signal(str)
    response_completed = Signal(str)
    response_error = Signal(str)
    
    def __init__(
        self,
        config: Optional[OpenRouterConfig] = None,
        parent: Optional[QObject] = None,
    ):
        """Initialize the LangChain service.
        
        Args:
            config: OpenRouter configuration. If None, loads from settings/keyring.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self._config = config
        self._worker: Optional[LangChainWorker] = None
    
    @property
    def config(self) -> OpenRouterConfig:
        """Get the OpenRouter configuration, loading from settings if needed."""
        if self._config is None:
            self._config = OpenRouterConfig.from_settings()
        return self._config
    
    def is_configured(self) -> bool:
        """Check if the service is properly configured."""
        try:
            config = self.config
            return (
                config.api_key 
                and config.api_key != "YOUR_API_KEY_HERE"
            )
        except ValueError:
            return False
    
    def send_message(
        self,
        agent: Agent,
        memories: List[AgentMemory],
        workspace_memories: Optional[str],
        rag_context: Optional[str],
        messages: List[Message],
        image_data_uris: Optional[List[str]] = None,
    ) -> None:
        """Send messages to the LLM with agent context.
        
        Args:
            agent: The agent configuration.
            memories: Agent memories to inject.
            workspace_memories: Workspace memories to inject.
            rag_context: RAG context snippets to inject.
            messages: List of messages to send.
            image_data_uris: Optional list of base64 data URIs for image attachments.
        """
        # Cancel any existing request
        self.cancel()
        
        # Create and start worker
        self._worker = LangChainWorker(
            self.config, agent, memories, workspace_memories, rag_context, messages, image_data_uris, self
        )
        self._worker.chunk_received.connect(self.response_chunk.emit)
        self._worker.completed.connect(self._on_completed)
        self._worker.error.connect(self._on_error)
        self._worker.start()
    
    def _on_completed(self, response: str) -> None:
        """Handle completion of the request."""
        self.response_completed.emit(response)
        self._cleanup_worker()

    def _on_error(self, error_msg: str) -> None:
        """Handle error during request."""
        self.response_error.emit(error_msg)
        self._cleanup_worker()
    
    def cancel(self) -> None:
        """Cancel the current request."""
        self._cleanup_worker()

    def _cleanup_worker(self) -> None:
        """Clean up the worker instance."""
        if self._worker is not None:
            # Disconnect signals
            try:
                self._worker.chunk_received.disconnect(self.response_chunk.emit)
                self._worker.completed.disconnect(self._on_completed)
                self._worker.error.disconnect(self._on_error)
            except (RuntimeError, TypeError):
                pass
            
            self._worker.cancel()
            self._worker.finished.connect(self._worker.deleteLater)
            if not self._worker.isRunning():
                self._worker.deleteLater()
            self._worker = None
