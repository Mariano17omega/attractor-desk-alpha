"""ModelSettings - LLM model configuration and API key management."""

from __future__ import annotations

import json
from typing import Optional

from PySide6.QtCore import QObject, Signal

from core.constants import DEFAULT_MODEL
from core.infrastructure.keyring_service import KeyringService, get_keyring_service
from core.persistence import Database, SettingsRepository


DEFAULT_MODELS = [
    "anthropic/claude-3.5-sonnet",
    "anthropic/claude-3-opus",
    "anthropic/claude-3-haiku",
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "openai/gpt-4-turbo",
    "google/gemini-pro-1.5",
    "google/gemini-flash-1.5",
    "meta-llama/llama-3.1-70b-instruct",
    "meta-llama/llama-3.1-8b-instruct",
    "mistralai/mixtral-8x7b-instruct",
    "deepseek/deepseek-chat",
]

DEFAULT_IMAGE_MODELS = [
    "anthropic/claude-3.5-sonnet",
    "anthropic/claude-3-opus",
    "anthropic/claude-3-haiku",
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "openai/gpt-4-turbo",
    "google/gemini-pro-1.5",
    "google/gemini-flash-1.5",
]


class ModelSettings(QObject):
    """Manages LLM model selection and API key configuration."""

    settings_changed = Signal()

    KEY_DEFAULT_MODEL = "models.default"
    KEY_IMAGE_MODEL = "models.image_model"
    KEY_MODEL_LIST = "models.list"
    KEY_IMAGE_MODEL_LIST = "models.image_list"
    KEY_API_KEY = "models.api_key"  # Fallback for non-keyring environments

    def __init__(
        self,
        database: Optional[Database] = None,
        keyring_service: Optional[KeyringService] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._db = database or Database()
        self._repo = SettingsRepository(self._db)
        self._keyring = keyring_service or get_keyring_service()

        # Internal state
        self._api_key: str = ""
        self._default_model: str = DEFAULT_MODEL
        self._image_model: str = DEFAULT_IMAGE_MODELS[0]
        self._models: list[str] = DEFAULT_MODELS.copy()
        self._image_models: list[str] = DEFAULT_IMAGE_MODELS.copy()

    @property
    def keyring_available(self) -> bool:
        """Check if the keyring backend is available."""
        return self._keyring.is_available

    @property
    def has_openrouter_key(self) -> bool:
        """Check if OpenRouter API key is configured."""
        return bool(self._api_key) or self._keyring.has_credential("openrouter")

    @property
    def api_key(self) -> str:
        """Get OpenRouter API key."""
        return self._api_key

    @api_key.setter
    def api_key(self, value: str) -> None:
        """Set OpenRouter API key."""
        value = value or ""
        if self._api_key != value:
            self._api_key = value
            self.settings_changed.emit()

    @property
    def default_model(self) -> str:
        """Get default LLM model."""
        return self._default_model

    @default_model.setter
    def default_model(self, value: str) -> None:
        """Set default LLM model."""
        if value and self._default_model != value:
            self._default_model = value
            self.settings_changed.emit()

    @property
    def image_model(self) -> str:
        """Get image/multimodal model."""
        return self._image_model

    @image_model.setter
    def image_model(self, value: str) -> None:
        """Set image/multimodal model."""
        if value and self._image_model != value:
            self._image_model = value
            self.settings_changed.emit()

    @property
    def models(self) -> list[str]:
        """Get list of available models."""
        return self._models.copy()

    def add_model(self, model_id: str) -> None:
        """Add a custom model to the list."""
        model_id = model_id.strip()
        if not model_id or model_id in self._models:
            return
        self._models.append(model_id)
        self.settings_changed.emit()

    @property
    def image_models(self) -> list[str]:
        """Get list of available image models."""
        return self._image_models.copy()

    def add_image_model(self, model_id: str) -> None:
        """Add a custom image model to the list."""
        model_id = model_id.strip()
        if not model_id or model_id in self._image_models:
            return
        self._image_models.append(model_id)
        self.settings_changed.emit()

    def load(self) -> None:
        """Load model settings from database and keyring."""
        # Load model configuration from database
        self._default_model = self._repo.get_value(self.KEY_DEFAULT_MODEL, DEFAULT_MODEL)
        self._image_model = self._repo.get_value(
            self.KEY_IMAGE_MODEL, DEFAULT_IMAGE_MODELS[0]
        )

        # Load API key from keyring, with fallback to SQLite when keyring is unavailable
        self._api_key = self._keyring.get_credential("openrouter") or ""
        if not self._keyring.is_available and not self._api_key:
            self._api_key = self._repo.get_value(self.KEY_API_KEY, "")

        # Load model lists from JSON
        model_list = self._repo.get_value(self.KEY_MODEL_LIST, "")
        if model_list:
            try:
                parsed = json.loads(model_list)
                if isinstance(parsed, list) and parsed:
                    self._models = [str(item) for item in parsed]
            except json.JSONDecodeError:
                self._models = DEFAULT_MODELS.copy()
        else:
            self._models = DEFAULT_MODELS.copy()

        image_model_list = self._repo.get_value(self.KEY_IMAGE_MODEL_LIST, "")
        if image_model_list:
            try:
                parsed = json.loads(image_model_list)
                if isinstance(parsed, list) and parsed:
                    self._image_models = [str(item) for item in parsed]
            except json.JSONDecodeError:
                self._image_models = DEFAULT_IMAGE_MODELS.copy()
        else:
            self._image_models = DEFAULT_IMAGE_MODELS.copy()

    def save(self) -> None:
        """Save model settings to database and keyring."""
        # Store API key in keyring when available; fallback to SQLite in headless mode
        if self._keyring.is_available:
            if self._api_key:
                self._keyring.store_credential("openrouter", self._api_key)
        else:
            # Fallback to plaintext SQLite storage (security warning in CODE_REVIEW.md)
            self._repo.set(self.KEY_API_KEY, self._api_key, "models")

        # Save model configuration
        self._repo.set(self.KEY_DEFAULT_MODEL, self._default_model, "models")
        self._repo.set(self.KEY_IMAGE_MODEL, self._image_model, "models")
        self._repo.set(self.KEY_MODEL_LIST, json.dumps(self._models), "models")
        self._repo.set(
            self.KEY_IMAGE_MODEL_LIST, json.dumps(self._image_models), "models"
        )

    def snapshot(self) -> dict[str, object]:
        """Create snapshot of current state for revert functionality."""
        return {
            "api_key": self._api_key,
            "default_model": self._default_model,
            "image_model": self._image_model,
            "models": self._models.copy(),
            "image_models": self._image_models.copy(),
        }

    def restore_snapshot(self, snapshot: dict[str, object]) -> None:
        """Restore state from snapshot, emitting signals for changes."""
        self._api_key = snapshot.get("api_key", "") or ""
        self._default_model = snapshot.get("default_model", DEFAULT_MODEL)
        self._image_model = snapshot.get("image_model", DEFAULT_IMAGE_MODELS[0])
        self._models = list(snapshot.get("models", DEFAULT_MODELS.copy()))
        self._image_models = list(
            snapshot.get("image_models", DEFAULT_IMAGE_MODELS.copy())
        )
        self.settings_changed.emit()
