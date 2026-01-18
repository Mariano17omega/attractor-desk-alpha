"""Settings subsystem - Decomposed settings management."""

from .appearance_settings import AppearanceSettings
from .coordinator import SettingsCoordinator
from .deep_search_settings import DeepSearchSettings
from .model_settings import ModelSettings, DEFAULT_MODELS, DEFAULT_IMAGE_MODELS
from .shortcuts_settings import ShortcutsSettings, DEFAULT_SHORTCUT_DEFINITIONS
from .ui_visibility_settings import UIVisibilitySettings

__all__ = [
    "AppearanceSettings",
    "DeepSearchSettings",
    "ModelSettings",
    "SettingsCoordinator",
    "ShortcutsSettings",
    "UIVisibilitySettings",
    "DEFAULT_MODELS",
    "DEFAULT_IMAGE_MODELS",
    "DEFAULT_SHORTCUT_DEFINITIONS",
]
