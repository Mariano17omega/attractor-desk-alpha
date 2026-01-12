"""OpenRouter API client for LLM interactions."""

from dataclasses import dataclass
from typing import AsyncIterator, List, Optional

import httpx

from ..persistence import Database, SettingsRepository
from .keyring_service import KeyringService

DEFAULT_MODEL = "openai/gpt-4o"
SETTINGS_DEFAULT_MODEL_KEY = "models.default"


@dataclass
class ChatMessage:
    """A message in the OpenRouter chat format."""
    role: str
    content: str


@dataclass
class OpenRouterConfig:
    """Configuration for the OpenRouter client."""
    api_key: str
    model: str
    base_url: str = "https://openrouter.ai/api/v1"
    
    @classmethod
    def from_settings(
        cls,
        settings_repo: Optional[SettingsRepository] = None,
        keyring_service: Optional[KeyringService] = None,
    ) -> "OpenRouterConfig":
        """Load configuration from settings database and keyring.
        
        Args:
            settings_repo: Settings repository instance.
            keyring_service: Keyring service for API key retrieval.
            
        Returns:
            OpenRouterConfig instance.
            
        Raises:
            ValueError: If the API key is missing or keyring is unavailable.
        """
        settings_repo = settings_repo or SettingsRepository(Database())
        keyring_service = keyring_service or KeyringService()
        
        api_key = keyring_service.get_api_key()
        if not api_key:
            raise ValueError(
                "OpenRouter API key is not configured in the system keyring."
            )
        
        model = settings_repo.get_value(SETTINGS_DEFAULT_MODEL_KEY, DEFAULT_MODEL).strip()
        if not model:
            model = DEFAULT_MODEL
        
        return cls(
            api_key=api_key,
            model=model,
        )


class OpenRouterClient:
    """Client for interacting with the OpenRouter API."""
    
    def __init__(self, config: OpenRouterConfig):
        """Initialize the client with configuration.
        
        Args:
            config: OpenRouter configuration.
        """
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://attractor-desk.app",
                    "X-Title": "Attractor Desk",
                },
                timeout=60.0,
            )
        return self._client
    
    async def chat_completion(
        self,
        messages: List[ChatMessage],
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """Send a chat completion request.
        
        Args:
            messages: List of chat messages.
            stream: Whether to stream the response.
            
        Yields:
            Response content chunks.
        """
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ],
            "stream": stream,
        }
        
        if stream:
            async with self.client.stream(
                "POST",
                "/chat/completions",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            import json
                            chunk = json.loads(data)
                            if "choices" in chunk and chunk["choices"]:
                                delta = chunk["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
        else:
            response = await self.client.post(
                "/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            if "choices" in data and data["choices"]:
                content = data["choices"][0].get("message", {}).get("content", "")
                yield content
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
