"""ViewModel for settings management."""

from __future__ import annotations

import json
from typing import Optional

from PySide6.QtCore import QObject, Signal

from core.constants import DEFAULT_MODEL
from core.models import ThemeMode
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


class SettingsViewModel(QObject):
    """ViewModel for managing application settings."""

    settings_changed = Signal()
    settings_saved = Signal()
    error_occurred = Signal(str)
    theme_changed = Signal(ThemeMode)
    transparency_changed = Signal(int)
    keep_above_changed = Signal(bool)

    KEY_THEME_MODE = "theme.mode"
    KEY_FONT_FAMILY = "theme.font_family"
    KEY_TRANSPARENCY = "theme.transparency"
    KEY_KEEP_ABOVE = "theme.keep_above"
    KEY_DEFAULT_MODEL = "models.default"
    KEY_MODEL_LIST = "models.list"
    KEY_API_KEY = "models.api_key"

    def __init__(
        self,
        settings_db: Optional[Database] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._settings_db = settings_db or Database()
        self._settings_repo = SettingsRepository(self._settings_db)

        self._theme_mode: ThemeMode = ThemeMode.DARK
        self._font_family: str = "Segoe UI"
        self._transparency: int = 100
        self._keep_above: bool = False
        self._api_key: str = ""
        self._default_model: str = DEFAULT_MODEL
        self._models: list[str] = DEFAULT_MODELS.copy()

        self._saved_state: dict[str, object] = {}
        self.load_settings()

    @property
    def theme_mode(self) -> ThemeMode:
        return self._theme_mode

    @theme_mode.setter
    def theme_mode(self, value: ThemeMode | str) -> None:
        try:
            mode = value if isinstance(value, ThemeMode) else ThemeMode(str(value).lower())
        except (ValueError, TypeError):
            mode = ThemeMode.DARK
        if self._theme_mode != mode:
            self._theme_mode = mode
            self.theme_changed.emit(mode)
            self.settings_changed.emit()

    @property
    def font_family(self) -> str:
        return self._font_family

    @font_family.setter
    def font_family(self, value: str) -> None:
        if value and self._font_family != value:
            self._font_family = value
            self.settings_changed.emit()

    @property
    def transparency(self) -> int:
        return self._transparency

    @transparency.setter
    def transparency(self, value: int) -> None:
        value = max(30, min(100, int(value)))
        if self._transparency != value:
            self._transparency = value
            self.transparency_changed.emit(value)
            self.settings_changed.emit()

    @property
    def keep_above(self) -> bool:
        return self._keep_above

    @keep_above.setter
    def keep_above(self, value: bool) -> None:
        if self._keep_above != bool(value):
            self._keep_above = bool(value)
            self.keep_above_changed.emit(self._keep_above)
            self.settings_changed.emit()

    @property
    def api_key(self) -> str:
        return self._api_key

    @api_key.setter
    def api_key(self, value: str) -> None:
        value = value or ""
        if self._api_key != value:
            self._api_key = value
            self.settings_changed.emit()

    @property
    def default_model(self) -> str:
        return self._default_model

    @default_model.setter
    def default_model(self, value: str) -> None:
        if value and self._default_model != value:
            self._default_model = value
            self.settings_changed.emit()

    @property
    def models(self) -> list[str]:
        return self._models.copy()

    def add_model(self, model_id: str) -> None:
        model_id = model_id.strip()
        if not model_id or model_id in self._models:
            return
        self._models.append(model_id)
        self.settings_changed.emit()

    def snapshot(self) -> dict[str, object]:
        return {
            "theme_mode": self._theme_mode,
            "font_family": self._font_family,
            "transparency": self._transparency,
            "keep_above": self._keep_above,
            "api_key": self._api_key,
            "default_model": self._default_model,
            "models": self._models.copy(),
        }

    def restore_snapshot(self, snapshot: dict[str, object]) -> None:
        self._theme_mode = snapshot.get("theme_mode", ThemeMode.DARK)
        self._font_family = snapshot.get("font_family", "Segoe UI")
        self._transparency = int(snapshot.get("transparency", 100))
        self._keep_above = bool(snapshot.get("keep_above", False))
        self._api_key = snapshot.get("api_key", "") or ""
        self._default_model = snapshot.get("default_model", DEFAULT_MODEL)
        self._models = list(snapshot.get("models", DEFAULT_MODELS.copy()))

        self.theme_changed.emit(self._theme_mode)
        self.transparency_changed.emit(self._transparency)
        self.keep_above_changed.emit(self._keep_above)
        self.settings_changed.emit()

    def load_settings(self) -> None:
        theme_value = self._settings_repo.get_value(self.KEY_THEME_MODE, ThemeMode.DARK.value)
        try:
            self._theme_mode = ThemeMode(theme_value)
        except ValueError:
            self._theme_mode = ThemeMode.DARK

        self._font_family = self._settings_repo.get_value(self.KEY_FONT_FAMILY, "Segoe UI")
        self._transparency = self._settings_repo.get_int(self.KEY_TRANSPARENCY, 100)
        self._keep_above = self._settings_repo.get_bool(self.KEY_KEEP_ABOVE, False)
        self._api_key = self._settings_repo.get_value(self.KEY_API_KEY, "")
        self._default_model = self._settings_repo.get_value(self.KEY_DEFAULT_MODEL, DEFAULT_MODEL)

        model_list = self._settings_repo.get_value(self.KEY_MODEL_LIST, "")
        if model_list:
            try:
                parsed = json.loads(model_list)
                if isinstance(parsed, list) and parsed:
                    self._models = [str(item) for item in parsed]
            except json.JSONDecodeError:
                self._models = DEFAULT_MODELS.copy()

        self._saved_state = self.snapshot()

    def save_settings(self) -> None:
        try:
            self._settings_repo.set(
                self.KEY_THEME_MODE,
                self._theme_mode.value,
                "theme",
            )
            self._settings_repo.set(
                self.KEY_FONT_FAMILY,
                self._font_family,
                "theme",
            )
            self._settings_repo.set(
                self.KEY_TRANSPARENCY,
                str(self._transparency),
                "theme",
            )
            self._settings_repo.set(
                self.KEY_KEEP_ABOVE,
                str(self._keep_above).lower(),
                "theme",
            )
            self._settings_repo.set(
                self.KEY_API_KEY,
                self._api_key,
                "models",
            )
            self._settings_repo.set(
                self.KEY_DEFAULT_MODEL,
                self._default_model,
                "models",
            )
            self._settings_repo.set(
                self.KEY_MODEL_LIST,
                json.dumps(self._models),
                "models",
            )
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return

        self._saved_state = self.snapshot()
        self.settings_saved.emit()

    def revert_to_saved(self) -> None:
        """Restore values from last saved state."""
        self.restore_snapshot(self._saved_state.copy())
