"""OpenRouter embeddings client."""

from __future__ import annotations

from typing import Optional

import httpx

from core.config import get_openrouter_api_key
from core.constants import DEFAULT_EMBEDDING_MODEL


OPENROUTER_EMBEDDINGS_URL = "https://openrouter.ai/api/v1/embeddings"


class OpenRouterEmbeddings:
    """Lightweight OpenRouter embeddings client."""

    def __init__(
        self,
        model: str = DEFAULT_EMBEDDING_MODEL,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        body = {
            "model": self.model,
            "input": texts,
        }
        headers = {
            "Authorization": f"Bearer {self._get_api_key()}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://open-canvas-py.local",
            "X-Title": "Open Canvas Python",
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(OPENROUTER_EMBEDDINGS_URL, json=body, headers=headers)
            response.raise_for_status()
            data = response.json()
        embeddings = data.get("data", [])
        embeddings = sorted(embeddings, key=lambda item: item.get("index", 0))
        return [item.get("embedding", []) for item in embeddings]

    def embed_text(self, text: str) -> list[float]:
        embeddings = self.embed_texts([text])
        return embeddings[0] if embeddings else []

    def _get_api_key(self) -> str:
        if self.api_key:
            return self.api_key
        return get_openrouter_api_key()
