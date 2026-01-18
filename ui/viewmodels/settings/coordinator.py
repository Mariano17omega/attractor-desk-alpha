"""SettingsCoordinator - Facade for decomposed settings management.

This coordinator integrates the extracted settings subsystems with the legacy
SettingsViewModel during the refactoring. Once all subsystems are extracted,
this will replace SettingsViewModel entirely.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal

from core.models import ThemeMode
from core.persistence import Database
from core.infrastructure.keyring_service import KeyringService, get_keyring_service

from .appearance_settings import AppearanceSettings
from .deep_search_settings import DeepSearchSettings
from .model_settings import ModelSettings, DEFAULT_MODELS, DEFAULT_IMAGE_MODELS
from .shortcuts_settings import ShortcutsSettings, DEFAULT_SHORTCUT_DEFINITIONS
from .ui_visibility_settings import UIVisibilitySettings


class SettingsCoordinator(QObject):
    """
    Facade coordinating all settings subsystems.

    Phase 1: Appearance, shortcuts, UI visibility
    Phase 2: Models, deep search
    Phase 3+: RAG, global RAG, ChatPDF cleanup (future)
    """

    # Forward signals from subsystems
    theme_changed = Signal(ThemeMode)
    transparency_changed = Signal(int)
    keep_above_changed = Signal(bool)
    shortcuts_changed = Signal()
    deep_search_toggled = Signal(bool)
    settings_changed = Signal()
    settings_saved = Signal()
    error_occurred = Signal(str)

    def __init__(
        self,
        database: Optional[Database] = None,
        keyring_service: Optional[KeyringService] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)

        # Shared dependencies
        self._db = database or Database()
        self._keyring = keyring_service or get_keyring_service()

        # Phase 1 subsystems
        self.appearance = AppearanceSettings(self._db, parent=self)
        self.shortcuts = ShortcutsSettings(self._db, parent=self)
        self.ui_visibility = UIVisibilitySettings(self._db, parent=self)

        # Phase 2 subsystems
        self.models = ModelSettings(self._db, self._keyring, parent=self)
        self.deep_search = DeepSearchSettings(self._db, self._keyring, parent=self)

        # Track saved state for revert
        self._saved_state: dict[str, object] = {}

        # Wire up signal forwarding
        self._connect_signals()

    def _connect_signals(self) -> None:
        """Forward signals from subsystems to coordinator."""
        # Appearance signals
        self.appearance.theme_changed.connect(self.theme_changed)
        self.appearance.transparency_changed.connect(self.transparency_changed)
        self.appearance.keep_above_changed.connect(self.keep_above_changed)
        self.appearance.settings_changed.connect(self.settings_changed)

        # Shortcuts signals
        self.shortcuts.shortcuts_changed.connect(self.shortcuts_changed)
        self.shortcuts.settings_changed.connect(self.settings_changed)

        # UI visibility signals
        self.ui_visibility.settings_changed.connect(self.settings_changed)

        # Model settings signals
        self.models.settings_changed.connect(self.settings_changed)

        # Deep search signals
        self.deep_search.deep_search_toggled.connect(self.deep_search_toggled)
        self.deep_search.settings_changed.connect(self.settings_changed)

    def load_settings(self) -> None:
        """Load all settings from database."""
        self.appearance.load()
        self.shortcuts.load()
        self.ui_visibility.load()
        self.models.load()
        self.deep_search.load()
        self._saved_state = self.snapshot()

    def save_settings(self) -> None:
        """Save all settings to database."""
        try:
            self.appearance.save()
            self.shortcuts.save()
            self.ui_visibility.save()
            self.models.save()
            self.deep_search.save()
            self._saved_state = self.snapshot()
            self.settings_saved.emit()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def snapshot(self) -> dict[str, object]:
        """Create snapshot of all settings for revert functionality."""
        return {
            "appearance": self.appearance.snapshot(),
            "shortcuts": self.shortcuts.snapshot(),
            "ui_visibility": self.ui_visibility.snapshot(),
            "models": self.models.snapshot(),
            "deep_search": self.deep_search.snapshot(),
        }

    def restore_snapshot(self, snapshot: dict[str, object]) -> None:
        """Restore all settings from snapshot."""
        if "appearance" in snapshot:
            self.appearance.restore_snapshot(snapshot["appearance"])
        if "shortcuts" in snapshot:
            self.shortcuts.restore_snapshot(snapshot["shortcuts"])
        if "ui_visibility" in snapshot:
            self.ui_visibility.restore_snapshot(snapshot["ui_visibility"])
        if "models" in snapshot:
            self.models.restore_snapshot(snapshot["models"])
        if "deep_search" in snapshot:
            self.deep_search.restore_snapshot(snapshot["deep_search"])

    def revert_to_saved(self) -> None:
        """Restore all settings to last saved state."""
        self.restore_snapshot(self._saved_state.copy())

    # Convenience properties for backward compatibility

    @property
    def theme_mode(self) -> ThemeMode:
        """Get current theme mode."""
        return self.appearance.theme_mode

    @theme_mode.setter
    def theme_mode(self, value: ThemeMode | str) -> None:
        """Set theme mode."""
        self.appearance.theme_mode = value

    @property
    def font_family(self) -> str:
        """Get font family."""
        return self.appearance.font_family

    @font_family.setter
    def font_family(self, value: str) -> None:
        """Set font family."""
        self.appearance.font_family = value

    @property
    def transparency(self) -> int:
        """Get window transparency."""
        return self.appearance.transparency

    @transparency.setter
    def transparency(self, value: int) -> None:
        """Set window transparency."""
        self.appearance.transparency = value

    @property
    def keep_above(self) -> bool:
        """Get keep above flag."""
        return self.appearance.keep_above

    @keep_above.setter
    def keep_above(self, value: bool) -> None:
        """Set keep above flag."""
        self.appearance.keep_above = value

    @property
    def shortcut_definitions(self):
        """Get shortcut definitions."""
        return self.shortcuts.shortcut_definitions

    @property
    def shortcut_bindings(self) -> dict[str, str]:
        """Get shortcut bindings."""
        return self.shortcuts.shortcut_bindings

    def get_shortcut_sequence(self, action_id: str) -> str:
        """Get key sequence for action."""
        return self.shortcuts.get_shortcut_sequence(action_id)

    def set_shortcut_sequence(self, action_id: str, sequence: str) -> None:
        """Set key sequence for action."""
        self.shortcuts.set_shortcut_sequence(action_id, sequence)

    def reset_shortcuts(self) -> None:
        """Reset shortcuts to defaults."""
        self.shortcuts.reset_shortcuts()

    @property
    def sidebar_visible(self) -> bool:
        """Get sidebar visibility."""
        return self.ui_visibility.sidebar_visible

    @sidebar_visible.setter
    def sidebar_visible(self, value: bool) -> None:
        """Set sidebar visibility."""
        self.ui_visibility.sidebar_visible = value

    @property
    def artifact_panel_visible(self) -> bool:
        """Get artifact panel visibility."""
        return self.ui_visibility.artifact_panel_visible

    @artifact_panel_visible.setter
    def artifact_panel_visible(self, value: bool) -> None:
        """Set artifact panel visibility."""
        self.ui_visibility.artifact_panel_visible = value

    # Phase 2 backward compatibility properties

    @property
    def keyring_available(self) -> bool:
        """Check if keyring backend is available."""
        return self.models.keyring_available

    @property
    def has_openrouter_key(self) -> bool:
        """Check if OpenRouter API key is configured."""
        return self.models.has_openrouter_key

    @property
    def api_key(self) -> str:
        """Get OpenRouter API key."""
        return self.models.api_key

    @api_key.setter
    def api_key(self, value: str) -> None:
        """Set OpenRouter API key."""
        self.models.api_key = value

    @property
    def default_model(self) -> str:
        """Get default LLM model."""
        return self.models.default_model

    @default_model.setter
    def default_model(self, value: str) -> None:
        """Set default LLM model."""
        self.models.default_model = value

    @property
    def image_model(self) -> str:
        """Get image/multimodal model."""
        return self.models.image_model

    @image_model.setter
    def image_model(self, value: str) -> None:
        """Set image/multimodal model."""
        self.models.image_model = value

    @property
    def models_list(self) -> list[str]:
        """Get list of available models."""
        return self.models.models

    def add_model(self, model_id: str) -> None:
        """Add custom model to list."""
        self.models.add_model(model_id)

    @property
    def image_models_list(self) -> list[str]:
        """Get list of available image models."""
        return self.models.image_models

    def add_image_model(self, model_id: str) -> None:
        """Add custom image model to list."""
        self.models.add_image_model(model_id)

    @property
    def deep_search_enabled(self) -> bool:
        """Get deep search enabled state."""
        return self.deep_search.deep_search_enabled

    @deep_search_enabled.setter
    def deep_search_enabled(self, value: bool) -> None:
        """Set deep search enabled state."""
        self.deep_search.deep_search_enabled = value

    @property
    def exa_api_key(self) -> str:
        """Get Exa API key."""
        return self.deep_search.exa_api_key

    @exa_api_key.setter
    def exa_api_key(self, value: str) -> None:
        """Set Exa API key."""
        self.deep_search.exa_api_key = value

    @property
    def firecrawl_api_key(self) -> str:
        """Get Firecrawl API key."""
        return self.deep_search.firecrawl_api_key

    @firecrawl_api_key.setter
    def firecrawl_api_key(self, value: str) -> None:
        """Set Firecrawl API key."""
        self.deep_search.firecrawl_api_key = value

    @property
    def search_provider(self) -> str:
        """Get search provider."""
        return self.deep_search.search_provider

    @search_provider.setter
    def search_provider(self, value: str) -> None:
        """Set search provider."""
        self.deep_search.search_provider = value

    @property
    def deep_search_num_results(self) -> int:
        """Get number of search results."""
        return self.deep_search.deep_search_num_results

    @deep_search_num_results.setter
    def deep_search_num_results(self, value: int) -> None:
        """Set number of search results."""
        self.deep_search.deep_search_num_results = value
