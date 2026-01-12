"""ViewModel for settings management."""

from __future__ import annotations

import json
from typing import Optional

from PySide6.QtCore import QObject, Signal

from core.constants import DEFAULT_EMBEDDING_MODEL, DEFAULT_MODEL
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
    deep_search_toggled = Signal(bool)

    KEY_THEME_MODE = "theme.mode"
    KEY_FONT_FAMILY = "theme.font_family"
    KEY_TRANSPARENCY = "theme.transparency"
    KEY_KEEP_ABOVE = "theme.keep_above"
    KEY_DEFAULT_MODEL = "models.default"
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
        self._deep_search_enabled: bool = False
        self._exa_api_key: str = ""
        self._firecrawl_api_key: str = ""
        self._search_provider: str = "exa"
        self._deep_search_num_results: int = 5
        self._rag_enabled: bool = False
        self._rag_scope: str = "session"
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
        value = value if value in ("session", "workspace") else "session"
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

    def snapshot(self) -> dict[str, object]:
        return {
            "theme_mode": self._theme_mode,
            "font_family": self._font_family,
            "transparency": self._transparency,
            "keep_above": self._keep_above,
            "api_key": self._api_key,
            "default_model": self._default_model,
            "models": self._models.copy(),
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
        }

    def restore_snapshot(self, snapshot: dict[str, object]) -> None:
        self._theme_mode = snapshot.get("theme_mode", ThemeMode.DARK)
        self._font_family = snapshot.get("font_family", "Segoe UI")
        self._transparency = int(snapshot.get("transparency", 100))
        self._keep_above = bool(snapshot.get("keep_above", False))
        self._api_key = snapshot.get("api_key", "") or ""
        self._default_model = snapshot.get("default_model", DEFAULT_MODEL)
        self._models = list(snapshot.get("models", DEFAULT_MODELS.copy()))
        self._deep_search_enabled = bool(snapshot.get("deep_search_enabled", False))
        self._exa_api_key = snapshot.get("exa_api_key", "") or ""
        self._firecrawl_api_key = snapshot.get("firecrawl_api_key", "") or ""
        self._search_provider = snapshot.get("search_provider", "exa") or "exa"
        self._deep_search_num_results = int(snapshot.get("deep_search_num_results", 5))
        self._rag_enabled = bool(snapshot.get("rag_enabled", False))
        self._rag_scope = snapshot.get("rag_scope", "session") or "session"
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

        self.theme_changed.emit(self._theme_mode)
        self.transparency_changed.emit(self._transparency)
        self.keep_above_changed.emit(self._keep_above)
        self.deep_search_toggled.emit(self._deep_search_enabled)
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

        # Load Deep Search settings
        self._deep_search_enabled = self._settings_repo.get_bool(self.KEY_DEEP_SEARCH_ENABLED, False)
        self._exa_api_key = self._settings_repo.get_value(self.KEY_EXA_API_KEY, "")
        self._firecrawl_api_key = self._settings_repo.get_value(self.KEY_FIRECRAWL_API_KEY, "")
        self._search_provider = self._settings_repo.get_value(self.KEY_SEARCH_PROVIDER, "exa")
        self._deep_search_num_results = self._settings_repo.get_int(self.KEY_DEEP_SEARCH_NUM_RESULTS, 5)

        # Load RAG settings
        self._rag_enabled = self._settings_repo.get_bool(self.KEY_RAG_ENABLED, False)
        self._rag_scope = self._settings_repo.get_value(self.KEY_RAG_SCOPE, "session")
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
            # Save Deep Search settings
            self._settings_repo.set(
                self.KEY_DEEP_SEARCH_ENABLED,
                str(self._deep_search_enabled).lower(),
                "deep_search",
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
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return

        self._saved_state = self.snapshot()
        self.settings_saved.emit()

    def revert_to_saved(self) -> None:
        """Restore values from last saved state."""
        self.restore_snapshot(self._saved_state.copy())
