"""ViewModel for settings management."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal, QTimer

from core.constants import DEFAULT_EMBEDDING_MODEL, DEFAULT_MODEL
from core.infrastructure.keyring_service import KeyringService, get_keyring_service
from core.models import ShortcutDefinition, ThemeMode
from core.persistence import Database, SettingsRepository, RagRepository
from core.persistence.rag_repository import GLOBAL_WORKSPACE_ID
from core.services import GlobalRagService, GlobalRagIndexRequest, PdfWatcherService

logger = logging.getLogger(__name__)


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


class SettingsViewModel(QObject):
    """ViewModel for managing application settings."""

    settings_changed = Signal()
    settings_saved = Signal()
    error_occurred = Signal(str)
    theme_changed = Signal(ThemeMode)
    transparency_changed = Signal(int)
    keep_above_changed = Signal(bool)
    deep_search_toggled = Signal(bool)
    shortcuts_changed = Signal()
    keys_migrated = Signal(dict)  # Emitted after legacy key migration with results
    global_rag_progress = Signal(int, int, str)
    global_rag_complete = Signal(object)
    global_rag_error = Signal(str)
    global_rag_registry_updated = Signal()
    chatpdf_cleanup_complete = Signal(int)

    KEY_THEME_MODE = "theme.mode"
    KEY_FONT_FAMILY = "theme.font_family"
    KEY_TRANSPARENCY = "theme.transparency"
    KEY_KEEP_ABOVE = "theme.keep_above"
    KEY_DEFAULT_MODEL = "models.default"
    KEY_IMAGE_MODEL = "models.image_model"
    KEY_IMAGE_MODEL_LIST = "models.image_list"
    KEY_MODEL_LIST = "models.list"
    KEY_API_KEY = "models.api_key"
    KEY_DEEP_SEARCH_ENABLED = "deep_search.enabled"
    KEY_EXA_API_KEY = "deep_search.exa_api_key"
    KEY_FIRECRAWL_API_KEY = "deep_search.firecrawl_api_key"
    KEY_SEARCH_PROVIDER = "deep_search.provider"
    KEY_DEEP_SEARCH_NUM_RESULTS = "deep_search.num_results"
    KEY_RAG_ENABLED = "rag.enabled"
    KEY_RAG_SCOPE = "rag.scope"
    KEY_RAG_CHUNK_SIZE = "rag.chunk_size_chars"
    KEY_RAG_CHUNK_OVERLAP = "rag.chunk_overlap_chars"
    KEY_RAG_K_LEX = "rag.k_lex"
    KEY_RAG_K_VEC = "rag.k_vec"
    KEY_RAG_RRF_K = "rag.rrf_k"
    KEY_RAG_MAX_CANDIDATES = "rag.max_candidates"
    KEY_RAG_EMBEDDING_MODEL = "rag.embedding_model"
    KEY_RAG_ENABLE_QUERY_REWRITE = "rag.enable_query_rewrite"
    KEY_RAG_ENABLE_LLM_RERANK = "rag.enable_llm_rerank"
    KEY_RAG_INDEX_TEXT = "rag.index_text_artifacts"
    KEY_RAG_GLOBAL_FOLDER = "rag.global_folder"
    KEY_RAG_GLOBAL_MONITORING = "rag.global_monitoring_enabled"
    KEY_RAG_CHATPDF_RETENTION_DAYS = "rag.chatpdf_retention_days"
    KEY_SHORTCUT_BINDINGS = "shortcuts.bindings"
    KEY_SIDEBAR_VISIBLE = "ui.sidebar_visible"
    KEY_ARTIFACT_PANEL_VISIBLE = "ui.artifact_panel_visible"

    def __init__(
        self,
        settings_db: Optional[Database] = None,
        keyring_service: Optional[KeyringService] = None,
        chroma_service: Optional["ChromaService"] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._settings_db = settings_db or Database()
        self._settings_repo = SettingsRepository(self._settings_db)
        self._keyring_service = keyring_service or get_keyring_service()

        self._theme_mode: ThemeMode = ThemeMode.DARK
        self._font_family: str = "Segoe UI"
        self._transparency: int = 100
        self._keep_above: bool = False
        self._api_key: str = ""
        self._default_model: str = DEFAULT_MODEL
        self._default_model: str = DEFAULT_MODEL
        self._image_model: str = DEFAULT_IMAGE_MODELS[0]
        self._models: list[str] = DEFAULT_MODELS.copy()
        self._image_models: list[str] = DEFAULT_IMAGE_MODELS.copy()
        self._deep_search_enabled: bool = False
        self._exa_api_key: str = ""
        self._firecrawl_api_key: str = ""
        self._search_provider: str = "exa"
        self._deep_search_num_results: int = 5
        self._rag_enabled: bool = False
        self._rag_scope: str = "global"
        self._rag_chunk_size_chars: int = 1200
        self._rag_chunk_overlap_chars: int = 150
        self._rag_k_lex: int = 8
        self._rag_k_vec: int = 8
        self._rag_rrf_k: int = 60
        self._rag_max_candidates: int = 12
        self._rag_embedding_model: str = DEFAULT_EMBEDDING_MODEL
        self._rag_enable_query_rewrite: bool = False
        self._rag_enable_llm_rerank: bool = False
        self._rag_index_text_artifacts: bool = False
        self._rag_global_folder: str = str(Path.home() / "Documents" / "AttractorDeskRAG")
        self._rag_global_monitoring_enabled: bool = False
        self._rag_chatpdf_retention_days: int = 7
        self._shortcut_bindings: dict[str, str] = DEFAULT_SHORTCUT_BINDINGS.copy()
        self._sidebar_visible: bool = True
        self._artifact_panel_visible: bool = False

        self._saved_state: dict[str, object] = {}
        self._chroma_service = chroma_service
        self._rag_repository = RagRepository(self._settings_db)
        self._global_rag_service = GlobalRagService(self._rag_repository, chroma_service, self)
        self._global_rag_service.index_progress.connect(self._on_global_index_progress)
        self._global_rag_service.index_complete.connect(self._on_global_index_complete)
        self._global_rag_service.index_error.connect(self._on_global_index_error)
        self._pdf_watcher_service = PdfWatcherService(self)
        self._pdf_watcher_service.new_pdfs_detected.connect(self._on_global_pdfs_detected)
        self._pdf_watcher_service.watcher_error.connect(self.global_rag_error.emit)
        self._cleanup_timer = QTimer(self)
        self._cleanup_timer.setInterval(24 * 60 * 60 * 1000)
        self._cleanup_timer.timeout.connect(self._run_chatpdf_cleanup)
        self._cleanup_timer.start()
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
    def keyring_available(self) -> bool:
        """Check if the keyring backend is available."""
        return self._keyring_service.is_available

    @property
    def has_openrouter_key(self) -> bool:
        """Check if OpenRouter API key is configured."""
        return bool(self._api_key) or self._keyring_service.has_credential("openrouter")

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
    def image_model(self) -> str:
        return self._image_model

    @image_model.setter
    def image_model(self, value: str) -> None:
        if value and self._image_model != value:
            self._image_model = value
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

    @property
    def image_models(self) -> list[str]:
        return self._image_models.copy()

    def add_image_model(self, model_id: str) -> None:
        model_id = model_id.strip()
        if not model_id or model_id in self._image_models:
            return
        self._image_models.append(model_id)
        self.settings_changed.emit()

    @property
    def deep_search_enabled(self) -> bool:
        return self._deep_search_enabled

    @deep_search_enabled.setter
    def deep_search_enabled(self, value: bool) -> None:
        value = bool(value)
        if self._deep_search_enabled != value:
            self._deep_search_enabled = value
            self.deep_search_toggled.emit(value)
            self.settings_changed.emit()

    @property
    def exa_api_key(self) -> str:
        return self._exa_api_key

    @exa_api_key.setter
    def exa_api_key(self, value: str) -> None:
        value = value or ""
        if self._exa_api_key != value:
            self._exa_api_key = value
            self.settings_changed.emit()

    @property
    def deep_search_num_results(self) -> int:
        return self._deep_search_num_results

    @deep_search_num_results.setter
    def deep_search_num_results(self, value: int) -> None:
        value = max(1, min(20, int(value)))
        if self._deep_search_num_results != value:
            self._deep_search_num_results = value
            self.settings_changed.emit()

    @property
    def firecrawl_api_key(self) -> str:
        return self._firecrawl_api_key

    @firecrawl_api_key.setter
    def firecrawl_api_key(self, value: str) -> None:
        value = value or ""
        if self._firecrawl_api_key != value:
            self._firecrawl_api_key = value
            self.settings_changed.emit()

    @property
    def search_provider(self) -> str:
        return self._search_provider

    @search_provider.setter
    def search_provider(self, value: str) -> None:
        value = value if value in ("exa", "firecrawl") else "exa"
        if self._search_provider != value:
            self._search_provider = value
            self.settings_changed.emit()

    @property
    def rag_enabled(self) -> bool:
        return self._rag_enabled

    @rag_enabled.setter
    def rag_enabled(self, value: bool) -> None:
        value = bool(value)
        if self._rag_enabled != value:
            self._rag_enabled = value
            self.settings_changed.emit()

    @property
    def rag_scope(self) -> str:
        return self._rag_scope

    @rag_scope.setter
    def rag_scope(self, value: str) -> None:
        value = value if value in ("session", "workspace", "global") else "global"
        if self._rag_scope != value:
            self._rag_scope = value
            self.settings_changed.emit()

    @property
    def rag_chunk_size_chars(self) -> int:
        return self._rag_chunk_size_chars

    @rag_chunk_size_chars.setter
    def rag_chunk_size_chars(self, value: int) -> None:
        value = max(200, min(5000, int(value)))
        if self._rag_chunk_size_chars != value:
            self._rag_chunk_size_chars = value
            if self._rag_chunk_overlap_chars >= value:
                self._rag_chunk_overlap_chars = max(0, value - 1)
            self.settings_changed.emit()

    @property
    def rag_chunk_overlap_chars(self) -> int:
        return self._rag_chunk_overlap_chars

    @rag_chunk_overlap_chars.setter
    def rag_chunk_overlap_chars(self, value: int) -> None:
        value = max(0, min(1000, int(value)))
        if value >= self._rag_chunk_size_chars:
            value = max(0, self._rag_chunk_size_chars - 1)
        if self._rag_chunk_overlap_chars != value:
            self._rag_chunk_overlap_chars = value
            self.settings_changed.emit()

    @property
    def rag_k_lex(self) -> int:
        return self._rag_k_lex

    @rag_k_lex.setter
    def rag_k_lex(self, value: int) -> None:
        value = max(1, min(50, int(value)))
        if self._rag_k_lex != value:
            self._rag_k_lex = value
            self.settings_changed.emit()

    @property
    def rag_k_vec(self) -> int:
        return self._rag_k_vec

    @rag_k_vec.setter
    def rag_k_vec(self, value: int) -> None:
        value = max(0, min(50, int(value)))
        if self._rag_k_vec != value:
            self._rag_k_vec = value
            self.settings_changed.emit()

    @property
    def rag_rrf_k(self) -> int:
        return self._rag_rrf_k

    @rag_rrf_k.setter
    def rag_rrf_k(self, value: int) -> None:
        value = max(10, min(200, int(value)))
        if self._rag_rrf_k != value:
            self._rag_rrf_k = value
            self.settings_changed.emit()

    @property
    def rag_max_candidates(self) -> int:
        return self._rag_max_candidates

    @rag_max_candidates.setter
    def rag_max_candidates(self, value: int) -> None:
        value = max(1, min(50, int(value)))
        if self._rag_max_candidates != value:
            self._rag_max_candidates = value
            self.settings_changed.emit()

    @property
    def rag_embedding_model(self) -> str:
        return self._rag_embedding_model

    @rag_embedding_model.setter
    def rag_embedding_model(self, value: str) -> None:
        value = (value or "").strip()
        if self._rag_embedding_model != value:
            self._rag_embedding_model = value
            self.settings_changed.emit()

    @property
    def rag_enable_query_rewrite(self) -> bool:
        return self._rag_enable_query_rewrite

    @rag_enable_query_rewrite.setter
    def rag_enable_query_rewrite(self, value: bool) -> None:
        value = bool(value)
        if self._rag_enable_query_rewrite != value:
            self._rag_enable_query_rewrite = value
            self.settings_changed.emit()

    @property
    def rag_enable_llm_rerank(self) -> bool:
        return self._rag_enable_llm_rerank

    @rag_enable_llm_rerank.setter
    def rag_enable_llm_rerank(self, value: bool) -> None:
        value = bool(value)
        if self._rag_enable_llm_rerank != value:
            self._rag_enable_llm_rerank = value
            self.settings_changed.emit()

    @property
    def rag_index_text_artifacts(self) -> bool:
        return self._rag_index_text_artifacts

    @rag_index_text_artifacts.setter
    def rag_index_text_artifacts(self, value: bool) -> None:
        value = bool(value)
        if self._rag_index_text_artifacts != value:
            self._rag_index_text_artifacts = value
            self.settings_changed.emit()

    @property
    def rag_global_folder(self) -> str:
        return self._rag_global_folder

    @rag_global_folder.setter
    def rag_global_folder(self, value: str) -> None:
        value = (value or "").strip()
        if self._rag_global_folder != value:
            self._rag_global_folder = value
            self.settings_changed.emit()
            if self._rag_global_monitoring_enabled:
                self._start_global_monitoring()

    @property
    def rag_global_monitoring_enabled(self) -> bool:
        return self._rag_global_monitoring_enabled

    @rag_global_monitoring_enabled.setter
    def rag_global_monitoring_enabled(self, value: bool) -> None:
        value = bool(value)
        if self._rag_global_monitoring_enabled != value:
            self._rag_global_monitoring_enabled = value
            self.settings_changed.emit()
            if value:
                self._start_global_monitoring()
            else:
                self._pdf_watcher_service.stop()

    @property
    def rag_chatpdf_retention_days(self) -> int:
        return self._rag_chatpdf_retention_days

    @rag_chatpdf_retention_days.setter
    def rag_chatpdf_retention_days(self, value: int) -> None:
        value = max(1, min(90, int(value)))
        if self._rag_chatpdf_retention_days != value:
            self._rag_chatpdf_retention_days = value
            self.settings_changed.emit()

    @property
    def shortcut_definitions(self) -> list[ShortcutDefinition]:
        return DEFAULT_SHORTCUT_DEFINITIONS.copy()

    @property
    def shortcut_bindings(self) -> dict[str, str]:
        return self._shortcut_bindings.copy()

    def get_shortcut_sequence(self, action_id: str) -> str:
        return self._shortcut_bindings.get(action_id, "")

    def set_shortcut_sequence(self, action_id: str, sequence: str) -> None:
        if action_id not in DEFAULT_SHORTCUT_BINDINGS:
            return
        cleaned = (sequence or "").strip()
        if self._shortcut_bindings.get(action_id, "") != cleaned:
            self._shortcut_bindings[action_id] = cleaned
            self.shortcuts_changed.emit()
            self.settings_changed.emit()

    def reset_shortcuts(self) -> None:
        self._shortcut_bindings = DEFAULT_SHORTCUT_BINDINGS.copy()
        self.shortcuts_changed.emit()
        self.settings_changed.emit()

    @property
    def sidebar_visible(self) -> bool:
        return self._sidebar_visible

    @sidebar_visible.setter
    def sidebar_visible(self, value: bool) -> None:
        value = bool(value)
        if self._sidebar_visible != value:
            self._sidebar_visible = value
            self.settings_changed.emit()

    @property
    def artifact_panel_visible(self) -> bool:
        return self._artifact_panel_visible

    @artifact_panel_visible.setter
    def artifact_panel_visible(self, value: bool) -> None:
        value = bool(value)
        if self._artifact_panel_visible != value:
            self._artifact_panel_visible = value
            self.settings_changed.emit()

    def _normalize_shortcut_bindings(
        self, bindings: dict[str, object]
    ) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for definition in DEFAULT_SHORTCUT_DEFINITIONS:
            value = bindings.get(definition.action_id)
            if isinstance(value, str):
                normalized[definition.action_id] = value.strip()
            else:
                normalized[definition.action_id] = definition.default_sequence
        return normalized

    def snapshot(self) -> dict[str, object]:
        return {
            "theme_mode": self._theme_mode,
            "font_family": self._font_family,
            "transparency": self._transparency,
            "keep_above": self._keep_above,
            "api_key": self._api_key,
            "default_model": self._default_model,
            "image_model": self._image_model,
            "models": self._models.copy(),
            "image_models": self._image_models.copy(),
            "deep_search_enabled": self._deep_search_enabled,
            "exa_api_key": self._exa_api_key,
            "firecrawl_api_key": self._firecrawl_api_key,
            "search_provider": self._search_provider,
            "deep_search_num_results": self._deep_search_num_results,
            "rag_enabled": self._rag_enabled,
            "rag_scope": self._rag_scope,
            "rag_chunk_size_chars": self._rag_chunk_size_chars,
            "rag_chunk_overlap_chars": self._rag_chunk_overlap_chars,
            "rag_k_lex": self._rag_k_lex,
            "rag_k_vec": self._rag_k_vec,
            "rag_rrf_k": self._rag_rrf_k,
            "rag_max_candidates": self._rag_max_candidates,
            "rag_embedding_model": self._rag_embedding_model,
            "rag_enable_query_rewrite": self._rag_enable_query_rewrite,
            "rag_enable_llm_rerank": self._rag_enable_llm_rerank,
            "rag_index_text_artifacts": self._rag_index_text_artifacts,
            "rag_global_folder": self._rag_global_folder,
            "rag_global_monitoring_enabled": self._rag_global_monitoring_enabled,
            "rag_chatpdf_retention_days": self._rag_chatpdf_retention_days,
            "shortcut_bindings": self._shortcut_bindings.copy(),
        }

    def restore_snapshot(self, snapshot: dict[str, object]) -> None:
        self._theme_mode = snapshot.get("theme_mode", ThemeMode.DARK)
        self._font_family = snapshot.get("font_family", "Segoe UI")
        self._transparency = int(snapshot.get("transparency", 100))
        self._keep_above = bool(snapshot.get("keep_above", False))
        self._api_key = snapshot.get("api_key", "") or ""
        self._default_model = snapshot.get("default_model", DEFAULT_MODEL)
        self._image_model = snapshot.get("image_model", DEFAULT_IMAGE_MODELS[0])
        self._models = list(snapshot.get("models", DEFAULT_MODELS.copy()))
        self._image_models = list(snapshot.get("image_models", DEFAULT_IMAGE_MODELS.copy()))
        self._deep_search_enabled = bool(snapshot.get("deep_search_enabled", False))
        self._exa_api_key = snapshot.get("exa_api_key", "") or ""
        self._firecrawl_api_key = snapshot.get("firecrawl_api_key", "") or ""
        self._search_provider = snapshot.get("search_provider", "exa") or "exa"
        self._deep_search_num_results = int(snapshot.get("deep_search_num_results", 5))
        self._rag_enabled = bool(snapshot.get("rag_enabled", False))
        self._rag_scope = snapshot.get("rag_scope", "global") or "global"
        self._rag_chunk_size_chars = int(snapshot.get("rag_chunk_size_chars", 1200))
        self._rag_chunk_overlap_chars = int(snapshot.get("rag_chunk_overlap_chars", 150))
        self._rag_k_lex = int(snapshot.get("rag_k_lex", 8))
        self._rag_k_vec = int(snapshot.get("rag_k_vec", 8))
        self._rag_rrf_k = int(snapshot.get("rag_rrf_k", 60))
        self._rag_max_candidates = int(snapshot.get("rag_max_candidates", 12))
        self._rag_embedding_model = snapshot.get(
            "rag_embedding_model", DEFAULT_EMBEDDING_MODEL
        )
        self._rag_enable_query_rewrite = bool(
            snapshot.get("rag_enable_query_rewrite", False)
        )
        self._rag_enable_llm_rerank = bool(
            snapshot.get("rag_enable_llm_rerank", False)
        )
        self._rag_index_text_artifacts = bool(
            snapshot.get("rag_index_text_artifacts", False)
        )
        self._rag_global_folder = snapshot.get(
            "rag_global_folder",
            str(Path.home() / "Documents" / "AttractorDeskRAG"),
        )
        self._rag_global_monitoring_enabled = bool(
            snapshot.get("rag_global_monitoring_enabled", False)
        )
        self._rag_chatpdf_retention_days = int(
            snapshot.get("rag_chatpdf_retention_days", 7)
        )
        shortcuts = snapshot.get("shortcut_bindings", DEFAULT_SHORTCUT_BINDINGS.copy())
        if isinstance(shortcuts, dict):
            self._shortcut_bindings = self._normalize_shortcut_bindings(shortcuts)
        else:
            self._shortcut_bindings = DEFAULT_SHORTCUT_BINDINGS.copy()

        self.theme_changed.emit(self._theme_mode)
        self.transparency_changed.emit(self._transparency)
        self.keep_above_changed.emit(self._keep_above)
        self.deep_search_toggled.emit(self._deep_search_enabled)
        self.shortcuts_changed.emit()
        self.settings_changed.emit()
        if self._rag_global_monitoring_enabled:
            self._start_global_monitoring()
        else:
            self._pdf_watcher_service.stop()

    def load_settings(self) -> None:
        theme_value = self._settings_repo.get_value(self.KEY_THEME_MODE, ThemeMode.DARK.value)
        try:
            self._theme_mode = ThemeMode(theme_value)
        except ValueError:
            self._theme_mode = ThemeMode.DARK

        self._font_family = self._settings_repo.get_value(self.KEY_FONT_FAMILY, "Segoe UI")
        self._transparency = self._settings_repo.get_int(self.KEY_TRANSPARENCY, 100)
        self._keep_above = self._settings_repo.get_bool(self.KEY_KEEP_ABOVE, False)
        self._default_model = self._settings_repo.get_value(self.KEY_DEFAULT_MODEL, DEFAULT_MODEL)
        self._image_model = self._settings_repo.get_value(self.KEY_IMAGE_MODEL, DEFAULT_IMAGE_MODELS[0])

        # Load API keys from keyring, with fallback to SQLite when keyring is unavailable
        self._api_key = self._keyring_service.get_credential("openrouter") or ""
        self._exa_api_key = self._keyring_service.get_credential("exa") or ""
        self._firecrawl_api_key = self._keyring_service.get_credential("firecrawl") or ""
        if not self._keyring_service.is_available:
            if not self._api_key:
                self._api_key = self._settings_repo.get_value(self.KEY_API_KEY, "")
            if not self._exa_api_key:
                self._exa_api_key = self._settings_repo.get_value(self.KEY_EXA_API_KEY, "")
            if not self._firecrawl_api_key:
                self._firecrawl_api_key = self._settings_repo.get_value(
                    self.KEY_FIRECRAWL_API_KEY, ""
                )

        model_list = self._settings_repo.get_value(self.KEY_MODEL_LIST, "")
        if model_list:
            try:
                parsed = json.loads(model_list)
                if isinstance(parsed, list) and parsed:
                    self._models = [str(item) for item in parsed]
            except json.JSONDecodeError:
                self._models = DEFAULT_MODELS.copy()

        image_model_list = self._settings_repo.get_value(self.KEY_IMAGE_MODEL_LIST, "")
        if image_model_list:
            try:
                parsed = json.loads(image_model_list)
                if isinstance(parsed, list) and parsed:
                    self._image_models = [str(item) for item in parsed]
            except json.JSONDecodeError:
                self._image_models = DEFAULT_IMAGE_MODELS.copy()

        # Load Deep Search settings (non-secret parts from SQLite)
        self._deep_search_enabled = self._settings_repo.get_bool(self.KEY_DEEP_SEARCH_ENABLED, False)
        self._search_provider = self._settings_repo.get_value(self.KEY_SEARCH_PROVIDER, "exa")
        self._deep_search_num_results = self._settings_repo.get_int(self.KEY_DEEP_SEARCH_NUM_RESULTS, 5)

        # Load RAG settings
        self._rag_enabled = self._settings_repo.get_bool(self.KEY_RAG_ENABLED, False)
        self._rag_scope = self._settings_repo.get_value(self.KEY_RAG_SCOPE, "global")
        self._rag_chunk_size_chars = self._settings_repo.get_int(self.KEY_RAG_CHUNK_SIZE, 1200)
        self._rag_chunk_overlap_chars = self._settings_repo.get_int(
            self.KEY_RAG_CHUNK_OVERLAP,
            150,
        )
        if self._rag_chunk_overlap_chars >= self._rag_chunk_size_chars:
            self._rag_chunk_overlap_chars = max(0, self._rag_chunk_size_chars - 1)
        self._rag_k_lex = self._settings_repo.get_int(self.KEY_RAG_K_LEX, 8)
        self._rag_k_vec = self._settings_repo.get_int(self.KEY_RAG_K_VEC, 8)
        self._rag_rrf_k = self._settings_repo.get_int(self.KEY_RAG_RRF_K, 60)
        self._rag_max_candidates = self._settings_repo.get_int(
            self.KEY_RAG_MAX_CANDIDATES,
            12,
        )
        self._rag_embedding_model = self._settings_repo.get_value(
            self.KEY_RAG_EMBEDDING_MODEL,
            DEFAULT_EMBEDDING_MODEL,
        )
        self._rag_enable_query_rewrite = self._settings_repo.get_bool(
            self.KEY_RAG_ENABLE_QUERY_REWRITE,
            False,
        )
        self._rag_enable_llm_rerank = self._settings_repo.get_bool(
            self.KEY_RAG_ENABLE_LLM_RERANK,
            False,
        )
        self._rag_index_text_artifacts = self._settings_repo.get_bool(
            self.KEY_RAG_INDEX_TEXT,
            False,
        )
        self._rag_global_folder = self._settings_repo.get_value(
            self.KEY_RAG_GLOBAL_FOLDER,
            str(Path.home() / "Documents" / "AttractorDeskRAG"),
        )
        self._rag_global_monitoring_enabled = self._settings_repo.get_bool(
            self.KEY_RAG_GLOBAL_MONITORING,
            False,
        )
        self._rag_chatpdf_retention_days = self._settings_repo.get_int(
            self.KEY_RAG_CHATPDF_RETENTION_DAYS,
            7,
        )

        shortcut_data = self._settings_repo.get_value(self.KEY_SHORTCUT_BINDINGS, "")
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

        # Load UI visibility settings
        self._sidebar_visible = self._settings_repo.get_bool(self.KEY_SIDEBAR_VISIBLE, True)
        self._artifact_panel_visible = self._settings_repo.get_bool(
            self.KEY_ARTIFACT_PANEL_VISIBLE, False
        )

        self._saved_state = self.snapshot()
        if self._rag_global_monitoring_enabled:
            self._start_global_monitoring()
        else:
            self._pdf_watcher_service.stop()

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
            # Store API keys in keyring when available; fallback to SQLite in headless mode
            if self._keyring_service.is_available:
                if self._api_key:
                    self._keyring_service.store_credential("openrouter", self._api_key)
                if self._exa_api_key:
                    self._keyring_service.store_credential("exa", self._exa_api_key)
                if self._firecrawl_api_key:
                    self._keyring_service.store_credential("firecrawl", self._firecrawl_api_key)
            else:
                self._settings_repo.set(
                    self.KEY_API_KEY,
                    self._api_key,
                    "models",
                )
                self._settings_repo.set(
                    self.KEY_EXA_API_KEY,
                    self._exa_api_key,
                    "deep_search",
                )
                self._settings_repo.set(
                    self.KEY_FIRECRAWL_API_KEY,
                    self._firecrawl_api_key,
                    "deep_search",
                )
            self._settings_repo.set(
                self.KEY_DEFAULT_MODEL,
                self._default_model,
                "models",
            )
            self._settings_repo.set(
                self.KEY_IMAGE_MODEL,
                self._image_model,
                "models",
            )
            self._settings_repo.set(
                self.KEY_MODEL_LIST,
                json.dumps(self._models),
                "models",
            )
            self._settings_repo.set(
                self.KEY_IMAGE_MODEL_LIST,
                json.dumps(self._image_models),
                "models",
            )
            # Save Deep Search settings (non-secret parts to SQLite)
            self._settings_repo.set(
                self.KEY_DEEP_SEARCH_ENABLED,
                str(self._deep_search_enabled).lower(),
                "deep_search",
            )
            self._settings_repo.set(
                self.KEY_SEARCH_PROVIDER,
                self._search_provider,
                "deep_search",
            )
            self._settings_repo.set(
                self.KEY_SEARCH_PROVIDER,
                self._search_provider,
                "deep_search",
            )
            self._settings_repo.set(
                self.KEY_DEEP_SEARCH_NUM_RESULTS,
                str(self._deep_search_num_results),
                "deep_search",
            )
            # Save RAG settings
            self._settings_repo.set(
                self.KEY_RAG_ENABLED,
                str(self._rag_enabled).lower(),
                "rag",
            )
            self._settings_repo.set(
                self.KEY_RAG_SCOPE,
                self._rag_scope,
                "rag",
            )
            self._settings_repo.set(
                self.KEY_RAG_CHUNK_SIZE,
                str(self._rag_chunk_size_chars),
                "rag",
            )
            self._settings_repo.set(
                self.KEY_RAG_CHUNK_OVERLAP,
                str(self._rag_chunk_overlap_chars),
                "rag",
            )
            self._settings_repo.set(
                self.KEY_RAG_K_LEX,
                str(self._rag_k_lex),
                "rag",
            )
            self._settings_repo.set(
                self.KEY_RAG_K_VEC,
                str(self._rag_k_vec),
                "rag",
            )
            self._settings_repo.set(
                self.KEY_RAG_RRF_K,
                str(self._rag_rrf_k),
                "rag",
            )
            self._settings_repo.set(
                self.KEY_RAG_MAX_CANDIDATES,
                str(self._rag_max_candidates),
                "rag",
            )
            self._settings_repo.set(
                self.KEY_RAG_EMBEDDING_MODEL,
                self._rag_embedding_model,
                "rag",
            )
            self._settings_repo.set(
                self.KEY_RAG_ENABLE_QUERY_REWRITE,
                str(self._rag_enable_query_rewrite).lower(),
                "rag",
            )
            self._settings_repo.set(
                self.KEY_RAG_ENABLE_LLM_RERANK,
                str(self._rag_enable_llm_rerank).lower(),
                "rag",
            )
            self._settings_repo.set(
                self.KEY_RAG_INDEX_TEXT,
                str(self._rag_index_text_artifacts).lower(),
                "rag",
            )
            self._settings_repo.set(
                self.KEY_RAG_GLOBAL_FOLDER,
                self._rag_global_folder,
                "rag",
            )
            self._settings_repo.set(
                self.KEY_RAG_GLOBAL_MONITORING,
                str(self._rag_global_monitoring_enabled).lower(),
                "rag",
            )
            self._settings_repo.set(
                self.KEY_RAG_CHATPDF_RETENTION_DAYS,
                str(self._rag_chatpdf_retention_days),
                "rag",
            )
            self._settings_repo.set(
                self.KEY_SHORTCUT_BINDINGS,
                json.dumps(self._shortcut_bindings),
                "shortcuts",
            )
            # Save UI visibility settings
            self._settings_repo.set(
                self.KEY_SIDEBAR_VISIBLE,
                str(self._sidebar_visible).lower(),
                "ui",
            )
            self._settings_repo.set(
                self.KEY_ARTIFACT_PANEL_VISIBLE,
                str(self._artifact_panel_visible).lower(),
                "ui",
            )
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return

        self._saved_state = self.snapshot()
        self.settings_saved.emit()

    def revert_to_saved(self) -> None:
        """Restore values from last saved state."""
        self.restore_snapshot(self._saved_state.copy())

    def start_global_index(self, force_reindex: bool = False) -> None:
        if not self._rag_global_folder:
            self.global_rag_error.emit("Global RAG folder is not set")
            return
        request = self._build_global_request(force_reindex=force_reindex)
        self._global_rag_service.index_folder(self._rag_global_folder, request)

    def scan_global_folder(self) -> None:
        if not self._rag_global_folder:
            self.global_rag_error.emit("Global RAG folder is not set")
            return
        request = self._build_global_request(force_reindex=False)
        self._global_rag_service.index_folder(self._rag_global_folder, request)

    def list_global_registry_entries(self, status: Optional[str] = None):
        return self._global_rag_service.get_registry_entries(status=status)

    def get_global_registry_status_counts(self) -> dict[str, int]:
        return self._global_rag_service.get_registry_status_counts()

    def _build_global_request(self, force_reindex: bool) -> GlobalRagIndexRequest:
        return GlobalRagIndexRequest(
            workspace_id=GLOBAL_WORKSPACE_ID,
            pdf_paths=[],
            chunk_size_chars=self._rag_chunk_size_chars,
            chunk_overlap_chars=self._rag_chunk_overlap_chars,
            embedding_model=self._rag_embedding_model or DEFAULT_EMBEDDING_MODEL,
            embeddings_enabled=self._rag_enabled and self._rag_k_vec > 0,
            api_key=self._api_key or None,
            force_reindex=force_reindex,
        )

    def _start_global_monitoring(self) -> None:
        if not self._rag_global_folder:
            self.global_rag_error.emit("Global RAG folder is not set")
            return
        self._pdf_watcher_service.start(self._rag_global_folder)

    def _on_global_pdfs_detected(self, paths: list[str]) -> None:
        if not paths:
            return
        request = self._build_global_request(force_reindex=False)
        self._global_rag_service.index_paths(
            GlobalRagIndexRequest(
                workspace_id=request.workspace_id,
                pdf_paths=paths,
                chunk_size_chars=request.chunk_size_chars,
                chunk_overlap_chars=request.chunk_overlap_chars,
                embedding_model=request.embedding_model,
                embeddings_enabled=request.embeddings_enabled,
                api_key=request.api_key,
                force_reindex=False,
            )
        )

    def _on_global_index_progress(self, current: int, total: int, path: str) -> None:
        self.global_rag_progress.emit(current, total, path)

    def _on_global_index_complete(self, result: object) -> None:
        self.global_rag_complete.emit(result)
        self.global_rag_registry_updated.emit()

    def _on_global_index_error(self, error: str) -> None:
        self.global_rag_error.emit(error)
        self.global_rag_registry_updated.emit()

    def cleanup_chatpdf_documents(self) -> int:
        removed = self._run_chatpdf_cleanup()
        self.chatpdf_cleanup_complete.emit(removed)
        return removed

    def _run_chatpdf_cleanup(self) -> int:
        cutoff = datetime.now() - timedelta(days=self._rag_chatpdf_retention_days)
        stale_docs = self._rag_repository.list_stale_documents(cutoff)
        removed = 0
        for doc in stale_docs:
            if doc.source_path:
                try:
                    Path(doc.source_path).unlink(missing_ok=True)
                except OSError:
                    pass

            # Delete from SQLite
            self._rag_repository.delete_document(doc.id)

            # Also delete from ChromaDB (if available)
            if self._chroma_service is not None:
                try:
                    self._chroma_service.delete_by_document(doc.id)
                except Exception as exc:
                    logger.warning(f"Failed to delete document {doc.id} from ChromaDB: {exc}")

            removed += 1
        return removed

    def migrate_legacy_keys(self, legacy_file_path: Optional[Path] = None) -> dict[str, bool]:
        """
        Migrate API keys from legacy API_KEY.txt file to keyring.
        
        Args:
            legacy_file_path: Path to API_KEY.txt file. If None, uses default location.
            
        Returns:
            Dictionary mapping credential names to migration success (True/False).
            Empty dict if no migration needed or keyring unavailable.
        """
        if legacy_file_path is None:
            # Default to project root API_KEY.txt
            from core.config import get_config_path
            legacy_file_path = get_config_path()
        
        if not legacy_file_path.exists():
            return {}
        
        if not self._keyring_service.is_available:
            return {}
        
        results = self._keyring_service.migrate_from_file(legacy_file_path)
        
        if results:
            # Reload settings to pick up migrated keys
            self.load_settings()
            self.keys_migrated.emit(results)
        
        return results
