"""ShortcutsSettings - Keyboard shortcuts management."""

from __future__ import annotations

import json
from typing import Optional

from PySide6.QtCore import QObject, Signal

from core.models import ShortcutDefinition
from core.persistence import Database, SettingsRepository


DEFAULT_SHORTCUT_DEFINITIONS = [
    ShortcutDefinition(
        action_id="send_message",
        label="Send Message",
        description="Send the current message",
        default_sequence="Ctrl+Return",
    ),
    ShortcutDefinition(
        action_id="new_session",
        label="New Session",
        description="Start a new chat session",
        default_sequence="Ctrl+N",
    ),
    ShortcutDefinition(
        action_id="new_workspace",
        label="New Workspace",
        description="Create a new workspace",
        default_sequence="Ctrl+Shift+N",
    ),
    ShortcutDefinition(
        action_id="cancel_generation",
        label="Cancel Generation",
        description="Stop the current response",
        default_sequence="Esc",
    ),
    ShortcutDefinition(
        action_id="open_settings",
        label="Open Settings",
        description="Open the settings dialog",
        default_sequence="Ctrl+,",
    ),
    ShortcutDefinition(
        action_id="capture_full_screen",
        label="Capture Full Screen",
        description="Capture the active monitor",
        default_sequence="Ctrl+Shift+F",
    ),
    ShortcutDefinition(
        action_id="capture_region",
        label="Capture Region",
        description="Capture a selected screen region",
        default_sequence="Ctrl+Shift+R",
    ),
]

DEFAULT_SHORTCUT_BINDINGS = {
    definition.action_id: definition.default_sequence
    for definition in DEFAULT_SHORTCUT_DEFINITIONS
}


class ShortcutsSettings(QObject):
    """Manages keyboard shortcut bindings."""

    shortcuts_changed = Signal()
    settings_changed = Signal()

    KEY_SHORTCUT_BINDINGS = "shortcuts.bindings"

    def __init__(
        self,
        database: Optional[Database] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._db = database or Database()
        self._repo = SettingsRepository(self._db)

        # Internal state
        self._shortcut_bindings: dict[str, str] = DEFAULT_SHORTCUT_BINDINGS.copy()

    @property
    def shortcut_definitions(self) -> list[ShortcutDefinition]:
        """Get list of available shortcut definitions."""
        return DEFAULT_SHORTCUT_DEFINITIONS.copy()

    @property
    def shortcut_bindings(self) -> dict[str, str]:
        """Get current shortcut bindings."""
        return self._shortcut_bindings.copy()

    def get_shortcut_sequence(self, action_id: str) -> str:
        """Get key sequence for a specific action."""
        return self._shortcut_bindings.get(action_id, "")

    def set_shortcut_sequence(self, action_id: str, sequence: str) -> None:
        """Set key sequence for a specific action."""
        if action_id not in DEFAULT_SHORTCUT_BINDINGS:
            return

        cleaned = (sequence or "").strip()
        if self._shortcut_bindings.get(action_id, "") != cleaned:
            self._shortcut_bindings[action_id] = cleaned
            self.shortcuts_changed.emit()
            self.settings_changed.emit()

    def reset_shortcuts(self) -> None:
        """Reset all shortcuts to default values."""
        self._shortcut_bindings = DEFAULT_SHORTCUT_BINDINGS.copy()
        self.shortcuts_changed.emit()
        self.settings_changed.emit()

    def load(self) -> None:
        """Load shortcuts from database."""
        shortcut_data = self._repo.get_value(self.KEY_SHORTCUT_BINDINGS, "")
        if shortcut_data:
            try:
                parsed_shortcuts = json.loads(shortcut_data)
                if isinstance(parsed_shortcuts, dict):
                    self._shortcut_bindings = self._normalize_shortcut_bindings(
                        parsed_shortcuts
                    )
                else:
                    self._shortcut_bindings = DEFAULT_SHORTCUT_BINDINGS.copy()
            except json.JSONDecodeError:
                self._shortcut_bindings = DEFAULT_SHORTCUT_BINDINGS.copy()
        else:
            self._shortcut_bindings = DEFAULT_SHORTCUT_BINDINGS.copy()

    def save(self) -> None:
        """Save shortcuts to database."""
        self._repo.set(
            self.KEY_SHORTCUT_BINDINGS,
            json.dumps(self._shortcut_bindings),
            "shortcuts",
        )

    def snapshot(self) -> dict[str, object]:
        """Create snapshot of current state for revert functionality."""
        return {
            "shortcut_bindings": self._shortcut_bindings.copy(),
        }

    def restore_snapshot(self, snapshot: dict[str, object]) -> None:
        """Restore state from snapshot, emitting signals for changes."""
        shortcuts = snapshot.get("shortcut_bindings", DEFAULT_SHORTCUT_BINDINGS.copy())
        if isinstance(shortcuts, dict):
            self._shortcut_bindings = self._normalize_shortcut_bindings(shortcuts)
        else:
            self._shortcut_bindings = DEFAULT_SHORTCUT_BINDINGS.copy()

        self.shortcuts_changed.emit()
        self.settings_changed.emit()

    def _normalize_shortcut_bindings(
        self, bindings: dict[str, object]
    ) -> dict[str, str]:
        """Normalize and validate shortcut bindings."""
        normalized: dict[str, str] = {}
        for definition in DEFAULT_SHORTCUT_DEFINITIONS:
            value = bindings.get(definition.action_id)
            if isinstance(value, str):
                normalized[definition.action_id] = value.strip()
            else:
                normalized[definition.action_id] = definition.default_sequence
        return normalized
