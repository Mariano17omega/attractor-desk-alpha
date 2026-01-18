"""UIVisibilitySettings - UI panel visibility state."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal

from core.persistence import Database, SettingsRepository


class UIVisibilitySettings(QObject):
    """Manages UI panel visibility state."""

    settings_changed = Signal()

    KEY_SIDEBAR_VISIBLE = "ui.sidebar_visible"
    KEY_ARTIFACT_PANEL_VISIBLE = "ui.artifact_panel_visible"

    def __init__(
        self,
        database: Optional[Database] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._db = database or Database()
        self._repo = SettingsRepository(self._db)

        # Internal state
        self._sidebar_visible: bool = True
        self._artifact_panel_visible: bool = False

    @property
    def sidebar_visible(self) -> bool:
        """Get sidebar visibility state."""
        return self._sidebar_visible

    @sidebar_visible.setter
    def sidebar_visible(self, value: bool) -> None:
        """Set sidebar visibility state."""
        value = bool(value)
        if self._sidebar_visible != value:
            self._sidebar_visible = value
            self.settings_changed.emit()

    @property
    def artifact_panel_visible(self) -> bool:
        """Get artifact panel visibility state."""
        return self._artifact_panel_visible

    @artifact_panel_visible.setter
    def artifact_panel_visible(self, value: bool) -> None:
        """Set artifact panel visibility state."""
        value = bool(value)
        if self._artifact_panel_visible != value:
            self._artifact_panel_visible = value
            self.settings_changed.emit()

    def load(self) -> None:
        """Load UI visibility settings from database."""
        self._sidebar_visible = self._repo.get_bool(self.KEY_SIDEBAR_VISIBLE, True)
        self._artifact_panel_visible = self._repo.get_bool(
            self.KEY_ARTIFACT_PANEL_VISIBLE, False
        )

    def save(self) -> None:
        """Save UI visibility settings to database."""
        self._repo.set(
            self.KEY_SIDEBAR_VISIBLE,
            str(self._sidebar_visible).lower(),
            "ui",
        )
        self._repo.set(
            self.KEY_ARTIFACT_PANEL_VISIBLE,
            str(self._artifact_panel_visible).lower(),
            "ui",
        )

    def snapshot(self) -> dict[str, object]:
        """Create snapshot of current state for revert functionality."""
        return {
            "sidebar_visible": self._sidebar_visible,
            "artifact_panel_visible": self._artifact_panel_visible,
        }

    def restore_snapshot(self, snapshot: dict[str, object]) -> None:
        """Restore state from snapshot, emitting signals for changes."""
        self._sidebar_visible = bool(snapshot.get("sidebar_visible", True))
        self._artifact_panel_visible = bool(
            snapshot.get("artifact_panel_visible", False)
        )
        self.settings_changed.emit()
