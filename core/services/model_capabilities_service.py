"""Model capability lookup for multimodal support."""

from __future__ import annotations

from typing import Optional

import httpx

from core.config import get_openrouter_api_key


OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"


class ModelCapabilitiesService:
    """Resolve model capabilities via OpenRouter with heuristic fallbacks."""

    def __init__(self, timeout: float = 2.0):
        self._timeout = timeout
        self._model_supports_images: dict[str, bool] = {}
        self._cache_loaded = False
        self._last_api_key: Optional[str] = None

    def supports_images(self, model_name: str, api_key: Optional[str] = None) -> bool:
        model_name = (model_name or "").strip()
        if not model_name:
            return False

        cached = self._model_supports_images.get(model_name)
        if cached is not None:
            return cached

        resolved_key = api_key
        if resolved_key is None:
            try:
                resolved_key = get_openrouter_api_key()
            except ValueError:
                resolved_key = None
        if (not self._cache_loaded) or (resolved_key != self._last_api_key):
            self._fetch_model_capabilities(resolved_key)

        cached = self._model_supports_images.get(model_name)
        if cached is not None:
            return cached

        heuristic = self._heuristic_supports_images(model_name)
        self._model_supports_images[model_name] = heuristic
        return heuristic

    def _fetch_model_capabilities(self, api_key: Optional[str]) -> None:
        headers = {
            "Content-Type": "application/json",
            "HTTP-Referer": "https://open-canvas-py.local",
            "X-Title": "Open Canvas Python",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            response = httpx.get(
                OPENROUTER_MODELS_URL,
                headers=headers,
                timeout=self._timeout,
            )
            response.raise_for_status()
            payload = response.json()
            models = payload.get("data", payload)
            if isinstance(models, list):
                for model in models:
                    if not isinstance(model, dict):
                        continue
                    model_id = model.get("id") or model.get("model")
                    if not model_id or not isinstance(model_id, str):
                        continue
                    supports_images = self._extract_supports_images(model)
                    if supports_images is not None:
                        self._model_supports_images[model_id] = supports_images
        except Exception:
            pass
        finally:
            self._cache_loaded = True
            self._last_api_key = api_key

    @staticmethod
    def _extract_supports_images(model: dict) -> Optional[bool]:
        for key in ("input_modalities", "inputModalities", "modalities"):
            modalities = ModelCapabilitiesService._normalize_modalities(model.get(key))
            if modalities:
                return any(item in modalities for item in ("image", "vision", "multimodal"))

        capabilities = model.get("capabilities")
        if isinstance(capabilities, dict):
            for key in ("vision", "image", "multimodal"):
                value = capabilities.get(key)
                if isinstance(value, bool) and value:
                    return True

        architecture = model.get("architecture")
        if isinstance(architecture, dict):
            modality = architecture.get("modality") or architecture.get("input_modality")
            if isinstance(modality, str):
                lowered = modality.lower()
                if "image" in lowered or "vision" in lowered or "multi" in lowered:
                    return True

        return None

    @staticmethod
    def _normalize_modalities(value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item).lower() for item in value]
        if isinstance(value, dict):
            return [
                str(key).lower()
                for key, enabled in value.items()
                if bool(enabled)
            ]
        if isinstance(value, str):
            return [value.lower()]
        return []

    @staticmethod
    def _heuristic_supports_images(model_name: str) -> bool:
        lowered = model_name.lower()
        keywords = (
            "vision",
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-4v",
            "claude-3",
            "claude-3.5",
            "gemini",
            "llava",
            "pixtral",
            "qwen-vl",
            "idefics",
            "minicpm",
            "phi-3-vision",
        )
        return any(keyword in lowered for keyword in keywords)
