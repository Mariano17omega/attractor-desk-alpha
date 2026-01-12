"""LLM service wrapper for chat completions."""

import asyncio
from typing import List, Optional

from PySide6.QtCore import QObject, Signal, QThread

from ..core.models import Message, MessageRole
from .openrouter_client import OpenRouterClient, OpenRouterConfig, ChatMessage


class LLMWorker(QThread):
    """Worker thread for LLM API calls."""
    
    chunk_received = Signal(str)
    completed = Signal(str)
    error = Signal(str)
    
    def __init__(
        self,
        config: OpenRouterConfig,
        messages: List[ChatMessage],
        parent: Optional[QObject] = None,
    ):
        """Initialize the worker.
        
        Args:
            config: OpenRouter configuration.
            messages: Messages to send to the LLM.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self.config = config
        self.messages = messages
        self._cancelled = False
    
    def cancel(self) -> None:
        """Cancel the current request."""
        self._cancelled = True
    
    def run(self) -> None:
        """Execute the LLM request in a separate thread."""
        async def _run() -> None:
            client = OpenRouterClient(self.config)
            full_response = ""
            
            try:
                async for chunk in client.chat_completion(self.messages):
                    if self._cancelled:
                        break
                    full_response += chunk
                    self.chunk_received.emit(chunk)
                
                if not self._cancelled:
                    self.completed.emit(full_response)
            except Exception as e:
                self.error.emit(str(e))
            finally:
                await client.close()
        
        asyncio.run(_run())


class LLMService(QObject):
    """Service for managing LLM interactions."""
    
    response_chunk = Signal(str)
    response_completed = Signal(str)
    response_error = Signal(str)
    
    def __init__(self, config: Optional[OpenRouterConfig] = None, parent: Optional[QObject] = None):
        """Initialize the LLM service.
        
        Args:
            config: OpenRouter configuration. If None, loads from settings/keyring.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self._config = config
        self._worker: Optional[LLMWorker] = None
    
    @property
    def config(self) -> OpenRouterConfig:
        """Get the OpenRouter configuration, loading from settings if needed."""
        if self._config is None:
            self._config = OpenRouterConfig.from_settings()
        return self._config
    
    def is_configured(self) -> bool:
        """Check if the LLM service is properly configured."""
        try:
            config = self.config
            return (
                config.api_key 
                and config.api_key != "YOUR_API_KEY_HERE"
                and config.model
            )
        except ValueError:
            return False
    
    def send_message(self, messages: List[Message]) -> None:
        """Send messages to the LLM and stream the response.
        
        Args:
            messages: List of messages to send.
        """
        # Cancel any existing request
        self.cancel()
        
        # Convert to ChatMessage format
        chat_messages = [
            ChatMessage(role=msg.role.value, content=msg.content)
            for msg in messages
        ]
        
        # Create and start worker
        self._worker = LLMWorker(self.config, chat_messages, self)
        self._worker.chunk_received.connect(self.response_chunk.emit)
        self._worker.completed.connect(self._on_completed)
        self._worker.error.connect(self.response_error.emit)
        self._worker.start()
    
    def _on_completed(self, response: str) -> None:
        """Handle completion of the LLM request."""
        self.response_completed.emit(response)
        self._worker = None
    
    def cancel(self) -> None:
        """Cancel the current request."""
        if self._worker is not None:
            self._worker.cancel()
            self._worker.quit()
            self._worker.wait()
            self._worker = None
