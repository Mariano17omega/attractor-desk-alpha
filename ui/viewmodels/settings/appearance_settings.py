"""AppearanceSettings - UI theme, fonts, transparency, window behavior."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal

from core.models import ThemeMode
from core.persistence import Database, SettingsRepository


class AppearanceSettings(QObject):
    """Manages application appearance settings."""

    theme_changed = Signal(ThemeMode)
    transparency_changed = Signal(int)
    keep_above_changed = Signal(bool)
    settings_changed = Signal()

    KEY_THEME_MODE = "theme.mode"
    KEY_FONT_FAMILY = "theme.font_family"
    KEY_TRANSPARENCY = "theme.transparency"
    KEY_KEEP_ABOVE = "theme.keep_above"

    def __init__(
        self,
        database: Optional[Database] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._db = database or Database()
        self._repo = SettingsRepository(self._db)

        # Internal state
        self._theme_mode: ThemeMode = ThemeMode.DARK
        self._font_family: str = "Segoe UI"
        self._transparency: int = 100
        self._keep_above: bool = False

    @property
    def theme_mode(self) -> ThemeMode:
        """Get current theme mode."""
        return self._theme_mode

    @theme_mode.setter
    def theme_mode(self, value: ThemeMode | str) -> None:
        """Set theme mode."""
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
        """Get font family."""
        return self._font_family

    @font_family.setter
    def font_family(self, value: str) -> None:
        """Set font family."""
        if value and self._font_family != value:
            self._font_family = value
            self.settings_changed.emit()

    @property
    def transparency(self) -> int:
        """Get window transparency (30-100)."""
        return self._transparency

    @transparency.setter
    def transparency(self, value: int) -> None:
        """Set window transparency, clamped to 30-100."""
        value = max(30, min(100, int(value)))
        if self._transparency != value:
            self._transparency = value
            self.transparency_changed.emit(value)
            self.settings_changed.emit()

    @property
    def keep_above(self) -> bool:
        """Get keep above other windows flag."""
        return self._keep_above

    @keep_above.setter
    def keep_above(self, value: bool) -> None:
        """Set keep above other windows flag."""
        if self._keep_above != bool(value):
            self._keep_above = bool(value)
            self.keep_above_changed.emit(self._keep_above)
            self.settings_changed.emit()

    def load(self) -> None:
        """Load appearance settings from database."""
        theme_value = self._repo.get_value(self.KEY_THEME_MODE, ThemeMode.DARK.value)
        try:
            self._theme_mode = ThemeMode(theme_value)
        except ValueError:
            self._theme_mode = ThemeMode.DARK

        self._font_family = self._repo.get_value(self.KEY_FONT_FAMILY, "Segoe UI")
        self._transparency = self._repo.get_int(self.KEY_TRANSPARENCY, 100)
        self._keep_above = self._repo.get_bool(self.KEY_KEEP_ABOVE, False)

    def save(self) -> None:
        """Save appearance settings to database."""
        self._repo.set(self.KEY_THEME_MODE, self._theme_mode.value, "theme")
        self._repo.set(self.KEY_FONT_FAMILY, self._font_family, "theme")
        self._repo.set(self.KEY_TRANSPARENCY, str(self._transparency), "theme")
        self._repo.set(self.KEY_KEEP_ABOVE, str(self._keep_above).lower(), "theme")

    def snapshot(self) -> dict[str, object]:
        """Create snapshot of current state for revert functionality."""
        return {
            "theme_mode": self._theme_mode,
            "font_family": self._font_family,
            "transparency": self._transparency,
            "keep_above": self._keep_above,
        }

    def restore_snapshot(self, snapshot: dict[str, object]) -> None:
        """Restore state from snapshot, emitting signals for changes."""
        self._theme_mode = snapshot.get("theme_mode", ThemeMode.DARK)
        self._font_family = snapshot.get("font_family", "Segoe UI")
        self._transparency = int(snapshot.get("transparency", 100))
        self._keep_above = bool(snapshot.get("keep_above", False))

        # Emit signals to notify UI
        self.theme_changed.emit(self._theme_mode)
        self.transparency_changed.emit(self._transparency)
        self.keep_above_changed.emit(self._keep_above)
        self.settings_changed.emit()
