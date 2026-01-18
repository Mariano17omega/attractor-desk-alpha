"""DeepSearchSettings - Web search provider configuration."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal

from core.infrastructure.keyring_service import KeyringService, get_keyring_service
from core.persistence import Database, SettingsRepository


class DeepSearchSettings(QObject):
    """Manages deep search (Exa/Firecrawl) configuration."""

    deep_search_toggled = Signal(bool)
    settings_changed = Signal()

    KEY_DEEP_SEARCH_ENABLED = "deep_search.enabled"
    KEY_EXA_API_KEY = "deep_search.exa_api_key"  # Fallback for non-keyring
    KEY_FIRECRAWL_API_KEY = "deep_search.firecrawl_api_key"  # Fallback
    KEY_SEARCH_PROVIDER = "deep_search.provider"
    KEY_DEEP_SEARCH_NUM_RESULTS = "deep_search.num_results"

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
        self._deep_search_enabled: bool = False
        self._exa_api_key: str = ""
        self._firecrawl_api_key: str = ""
        self._search_provider: str = "exa"
        self._deep_search_num_results: int = 5

    @property
    def deep_search_enabled(self) -> bool:
        """Get deep search enabled state."""
        return self._deep_search_enabled

    @deep_search_enabled.setter
    def deep_search_enabled(self, value: bool) -> None:
        """Set deep search enabled state."""
        value = bool(value)
        if self._deep_search_enabled != value:
            self._deep_search_enabled = value
            self.deep_search_toggled.emit(value)
            self.settings_changed.emit()

    @property
    def exa_api_key(self) -> str:
        """Get Exa API key."""
        return self._exa_api_key

    @exa_api_key.setter
    def exa_api_key(self, value: str) -> None:
        """Set Exa API key."""
        value = value or ""
        if self._exa_api_key != value:
            self._exa_api_key = value
            self.settings_changed.emit()

    @property
    def firecrawl_api_key(self) -> str:
        """Get Firecrawl API key."""
        return self._firecrawl_api_key

    @firecrawl_api_key.setter
    def firecrawl_api_key(self, value: str) -> None:
        """Set Firecrawl API key."""
        value = value or ""
        if self._firecrawl_api_key != value:
            self._firecrawl_api_key = value
            self.settings_changed.emit()

    @property
    def search_provider(self) -> str:
        """Get search provider (exa or firecrawl)."""
        return self._search_provider

    @search_provider.setter
    def search_provider(self, value: str) -> None:
        """Set search provider."""
        value = value if value in ("exa", "firecrawl") else "exa"
        if self._search_provider != value:
            self._search_provider = value
            self.settings_changed.emit()

    @property
    def deep_search_num_results(self) -> int:
        """Get number of search results."""
        return self._deep_search_num_results

    @deep_search_num_results.setter
    def deep_search_num_results(self, value: int) -> None:
        """Set number of search results, clamped to 1-20."""
        value = max(1, min(20, int(value)))
        if self._deep_search_num_results != value:
            self._deep_search_num_results = value
            self.settings_changed.emit()

    def load(self) -> None:
        """Load deep search settings from database and keyring."""
        # Load API keys from keyring, with fallback to SQLite
        self._exa_api_key = self._keyring.get_credential("exa") or ""
        self._firecrawl_api_key = self._keyring.get_credential("firecrawl") or ""

        if not self._keyring.is_available:
            if not self._exa_api_key:
                self._exa_api_key = self._repo.get_value(self.KEY_EXA_API_KEY, "")
            if not self._firecrawl_api_key:
                self._firecrawl_api_key = self._repo.get_value(
                    self.KEY_FIRECRAWL_API_KEY, ""
                )

        # Load non-secret settings from database
        self._deep_search_enabled = self._repo.get_bool(
            self.KEY_DEEP_SEARCH_ENABLED, False
        )
        self._search_provider = self._repo.get_value(self.KEY_SEARCH_PROVIDER, "exa")
        self._deep_search_num_results = self._repo.get_int(
            self.KEY_DEEP_SEARCH_NUM_RESULTS, 5
        )

    def save(self) -> None:
        """Save deep search settings to database and keyring."""
        # Store API keys in keyring when available; fallback to SQLite
        if self._keyring.is_available:
            if self._exa_api_key:
                self._keyring.store_credential("exa", self._exa_api_key)
            if self._firecrawl_api_key:
                self._keyring.store_credential("firecrawl", self._firecrawl_api_key)
        else:
            # Fallback to plaintext SQLite storage (security warning in CODE_REVIEW.md)
            self._repo.set(self.KEY_EXA_API_KEY, self._exa_api_key, "deep_search")
            self._repo.set(
                self.KEY_FIRECRAWL_API_KEY, self._firecrawl_api_key, "deep_search"
            )

        # Save non-secret settings
        self._repo.set(
            self.KEY_DEEP_SEARCH_ENABLED,
            str(self._deep_search_enabled).lower(),
            "deep_search",
        )
        self._repo.set(self.KEY_SEARCH_PROVIDER, self._search_provider, "deep_search")
        self._repo.set(
            self.KEY_DEEP_SEARCH_NUM_RESULTS,
            str(self._deep_search_num_results),
            "deep_search",
        )

    def snapshot(self) -> dict[str, object]:
        """Create snapshot of current state for revert functionality."""
        return {
            "deep_search_enabled": self._deep_search_enabled,
            "exa_api_key": self._exa_api_key,
            "firecrawl_api_key": self._firecrawl_api_key,
            "search_provider": self._search_provider,
            "deep_search_num_results": self._deep_search_num_results,
        }

    def restore_snapshot(self, snapshot: dict[str, object]) -> None:
        """Restore state from snapshot, emitting signals for changes."""
        self._deep_search_enabled = bool(snapshot.get("deep_search_enabled", False))
        self._exa_api_key = snapshot.get("exa_api_key", "") or ""
        self._firecrawl_api_key = snapshot.get("firecrawl_api_key", "") or ""
        self._search_provider = snapshot.get("search_provider", "exa") or "exa"
        self._deep_search_num_results = int(snapshot.get("deep_search_num_results", 5))

        # Emit signals to notify changes
        self.deep_search_toggled.emit(self._deep_search_enabled)
        self.settings_changed.emit()
