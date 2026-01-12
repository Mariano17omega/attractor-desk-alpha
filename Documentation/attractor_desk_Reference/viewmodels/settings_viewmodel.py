"""ViewModel for settings management."""

import json
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot

from ..core.models import ThemeMode, ShortcutBinding
from ..persistence import Database, SettingsRepository
from ..infrastructure.keyring_service import KeyringService


# Default models available in OpenRouter
DEFAULT_MODELS = [
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "anthropic/claude-3.5-sonnet",
    "anthropic/claude-3-haiku",
    "google/gemini-2.0-flash-exp",
    "deepseek/deepseek-chat",
]

# Default embedding models available
DEFAULT_EMBEDDING_MODELS = [
    "openai/text-embedding-3-small",
    "openai/text-embedding-3-large",
    "cohere/embed-english-v3.0",
    "cohere/embed-multilingual-v3.0",
]


class SettingsViewModel(QObject):
    """ViewModel for managing application settings."""
    
    # Signals
    settings_changed = Signal()
    settings_saved = Signal()
    error_occurred = Signal(str)
    theme_changed = Signal(ThemeMode)
    transparency_changed = Signal(int)
    rag_settings_changed = Signal()
    
    # Setting keys
    KEY_THEME_MODE = "theme.mode"
    KEY_FONT_FAMILY = "theme.font_family"
    KEY_TRANSPARENCY = "theme.transparency"
    KEY_KEEP_ABOVE = "theme.keep_above"
    KEY_DEFAULT_MODEL = "models.default"
    KEY_MODEL_LIST = "models.list"
    KEY_SHORTCUTS = "shortcuts.bindings"
    KEY_MAX_WORKSPACE_MEMORY_TOKENS = "memory.max_workspace_tokens"
    KEY_MEMORY_AUTO_SUMMARIZE = "memory.auto_summarize"
    KEY_RAG_KNOWLEDGE_BASE_PATH = "rag.knowledge_base_path"
    KEY_RAG_CHUNK_SIZE = "rag.chunk_size"
    KEY_RAG_CHUNK_OVERLAP = "rag.chunk_overlap"
    KEY_RAG_TOP_K = "rag.top_k"
    KEY_RAG_EMBEDDING_MODEL = "rag.embedding_model"
    KEY_RAG_EMBEDDING_MODEL_LIST = "rag.embedding_model_list"
    KEY_RAG_EMBEDDING_BATCH_SIZE = "rag.embedding_batch_size"
    
    # Capture settings keys
    KEY_CAPTURE_STORAGE_PATH = "capture.storage_path"
    KEY_CAPTURE_RETENTION_DAYS = "capture.retention_days"
    KEY_CAPTURE_LAST_CLEANUP = "capture.last_cleanup"
    
    def __init__(
        self,
        settings_db: Optional[Database] = None,
        keyring_service: Optional[KeyringService] = None,
        parent: Optional[QObject] = None,
    ):
        """Initialize the SettingsViewModel.
        
        Args:
            settings_db: Settings database instance.
            keyring_service: Keyring service for secure storage.
            parent: Parent QObject.
        """
        super().__init__(parent)
        
        self._settings_db = settings_db or Database()
        self._settings_repo = SettingsRepository(self._settings_db)
        self._keyring_service = keyring_service or KeyringService()
        
        # Cached settings values
        self._theme_mode: ThemeMode = ThemeMode.DARK
        self._font_family: str = "Segoe UI"
        self._transparency: int = 100
        self._keep_above: bool = False
        self._api_key: str = ""
        self._default_model: str = DEFAULT_MODELS[0]
        self._models: list[str] = DEFAULT_MODELS.copy()
        self._shortcuts: list[ShortcutBinding] = ShortcutBinding.default_shortcuts()
        self._max_workspace_memory_tokens: int = 1500
        self._auto_summarize: bool = True
        
        # RAG settings
        from pathlib import Path
        self._rag_knowledge_base_path: str = str(Path.home() / "Documents" / "Doc_RAG")
        self._rag_chunk_size: int = 1000
        self._rag_chunk_overlap: int = 200
        self._rag_top_k: int = 4
        self._rag_top_k: int = 4
        self._rag_top_k: int = 4
        self._rag_embedding_model: str = "openai/text-embedding-3-small"
        self._rag_embedding_models: list[str] = DEFAULT_EMBEDDING_MODELS.copy()
        self._rag_embedding_batch_size: int = 20
        
        # Capture settings
        self._capture_storage_path: str = str(Path.home() / "Documents" / "temp_Attractor_Desk")
        self._capture_retention_days: int = 30
        self._capture_last_cleanup: str = ""
        
        # Load settings
        self.load_settings()
    
    # Properties
    @property
    def theme_mode(self) -> ThemeMode:
        """Get the current theme mode."""
        return self._theme_mode
    
    @theme_mode.setter
    def theme_mode(self, value: ThemeMode | str) -> None:
        """Set the theme mode."""
        try:
            mode = value if isinstance(value, ThemeMode) else ThemeMode(str(value).lower())
        except (ValueError, TypeError):
            mode = ThemeMode.DARK
        if self._theme_mode != mode:
            self._theme_mode = mode
            self.settings_changed.emit()
    
    @property
    def font_family(self) -> str:
        """Get the current font family."""
        return self._font_family
    
    @font_family.setter
    def font_family(self, value: str) -> None:
        """Set the font family."""
        if self._font_family != value:
            self._font_family = value
            self.settings_changed.emit()
    
    @property
    def transparency(self) -> int:
        """Get the window transparency (30-100)."""
        return self._transparency
    
    @transparency.setter
    def transparency(self, value: int) -> None:
        """Set the window transparency."""
        value = max(30, min(100, value))
        if self._transparency != value:
            self._transparency = value
            self.transparency_changed.emit(value)
            self.settings_changed.emit()
    
    @property
    def keep_above(self) -> bool:
        """Get whether to keep window above others."""
        return self._keep_above
    
    @keep_above.setter
    def keep_above(self, value: bool) -> None:
        """Set keep above preference."""
        if self._keep_above != value:
            self._keep_above = value
            self.settings_changed.emit()
    
    @property
    def api_key(self) -> str:
        """Get the API key."""
        return self._api_key
    
    @api_key.setter
    def api_key(self, value: str) -> None:
        """Set the API key."""
        if self._api_key != value:
            self._api_key = value
            self.settings_changed.emit()
    
    @property
    def api_key_set(self) -> bool:
        """Check if API key is set."""
        return bool(self._api_key) or self._keyring_service.has_api_key()
    
    @property
    def default_model(self) -> str:
        """Get the default model."""
        return self._default_model
    
    @default_model.setter
    def default_model(self, value: str) -> None:
        """Set the default model."""
        if self._default_model != value:
            self._default_model = value
            self.settings_changed.emit()
    
    @property
    def models(self) -> list[str]:
        """Get the list of available models."""
        return self._models.copy()
    
    @property
    def shortcuts(self) -> list[ShortcutBinding]:
        """Get the list of shortcut bindings."""
        return self._shortcuts.copy()

    @property
    def max_workspace_memory_tokens(self) -> int:
        """Get the max workspace memory token limit."""
        return self._max_workspace_memory_tokens

    @max_workspace_memory_tokens.setter
    def max_workspace_memory_tokens(self, value: int) -> None:
        """Set the max workspace memory token limit."""
        value = max(0, int(value))
        if self._max_workspace_memory_tokens != value:
            self._max_workspace_memory_tokens = value
            self.settings_changed.emit()

    @property
    def auto_summarize(self) -> bool:
        """Get whether auto-summarization is enabled."""
        return self._auto_summarize

    @auto_summarize.setter
    def auto_summarize(self, value: bool) -> None:
        """Set whether auto-summarization is enabled."""
        if self._auto_summarize != value:
            self._auto_summarize = value
            self.settings_changed.emit()
    
    @property
    def rag_knowledge_base_path(self) -> str:
        """Get the RAG knowledge base path."""
        return self._rag_knowledge_base_path
    
    @rag_knowledge_base_path.setter
    def rag_knowledge_base_path(self, value: str) -> None:
        """Set the RAG knowledge base path."""
        if self._rag_knowledge_base_path != value:
            self._rag_knowledge_base_path = value
            self.settings_changed.emit()
            self.rag_settings_changed.emit()
    
    @property
    def rag_chunk_size(self) -> int:
        """Get the RAG chunk size."""
        return self._rag_chunk_size
    
    @rag_chunk_size.setter
    def rag_chunk_size(self, value: int) -> None:
        """Set the RAG chunk size."""
        value = max(100, min(10000, value))
        if self._rag_chunk_size != value:
            self._rag_chunk_size = value
            self.settings_changed.emit()
            self.rag_settings_changed.emit()
    
    @property
    def rag_chunk_overlap(self) -> int:
        """Get the RAG chunk overlap."""
        return self._rag_chunk_overlap
    
    @rag_chunk_overlap.setter
    def rag_chunk_overlap(self, value: int) -> None:
        """Set the RAG chunk overlap."""
        value = max(0, min(self._rag_chunk_size // 2, value))
        if self._rag_chunk_overlap != value:
            self._rag_chunk_overlap = value
            self.settings_changed.emit()
            self.rag_settings_changed.emit()
    
    @property
    def rag_top_k(self) -> int:
        """Get the RAG top-k retrieval count."""
        return self._rag_top_k
    
    @rag_top_k.setter
    def rag_top_k(self, value: int) -> None:
        """Set the RAG top-k retrieval count."""
        value = max(1, min(20, value))
        if self._rag_top_k != value:
            self._rag_top_k = value
            self.settings_changed.emit()
            self.rag_settings_changed.emit()
    
    @property
    def rag_embedding_model(self) -> str:
        """Get the RAG embedding model."""
        return self._rag_embedding_model
    
    @rag_embedding_model.setter
    def rag_embedding_model(self, value: str) -> None:
        """Set the RAG embedding model."""
        if self._rag_embedding_model != value:
            self._rag_embedding_model = value
            self.settings_changed.emit()
            self.rag_settings_changed.emit()
    
    @property
    def rag_embedding_models(self) -> list[str]:
        """Get the list of available embedding models."""
        return self._rag_embedding_models.copy()
    
    @property
    def rag_embedding_batch_size(self) -> int:
        """Get the RAG embedding batch size."""
        return self._rag_embedding_batch_size
    
    @rag_embedding_batch_size.setter
    def rag_embedding_batch_size(self, value: int) -> None:
        """Set the RAG embedding batch size."""
        value = max(1, min(100, value))
        if self._rag_embedding_batch_size != value:
            self._rag_embedding_batch_size = value
            self.settings_changed.emit()
            self.rag_settings_changed.emit()
    
    @property
    def capture_storage_path(self) -> str:
        """Get the capture storage path."""
        return self._capture_storage_path
    
    @capture_storage_path.setter
    def capture_storage_path(self, value: str) -> None:
        """Set the capture storage path."""
        if self._capture_storage_path != value:
            self._capture_storage_path = value
            self.settings_changed.emit()
    
    @property
    def capture_retention_days(self) -> int:
        """Get the capture retention period in days."""
        return self._capture_retention_days
    
    @capture_retention_days.setter
    def capture_retention_days(self, value: int) -> None:
        """Set the capture retention period in days."""
        value = max(1, min(365, value))
        if self._capture_retention_days != value:
            self._capture_retention_days = value
            self.settings_changed.emit()
    
    @property
    def capture_last_cleanup(self) -> str:
        """Get the last capture cleanup timestamp (ISO format)."""
        return self._capture_last_cleanup
    
    @capture_last_cleanup.setter
    def capture_last_cleanup(self, value: str) -> None:
        """Set the last capture cleanup timestamp."""
        self._capture_last_cleanup = value
        # No emit - internal bookkeeping
    
    def is_model_multimodal(self, model_id: str) -> bool:
        """Check if a model supports multimodal (image) inputs.
        
        This queries the OpenRouter API to determine if the model
        supports image inputs (vision capability).
        
        Args:
            model_id: The model identifier.
            
        Returns:
            True if the model supports image inputs.
        """
        from ..infrastructure.model_capabilities_service import get_model_capabilities_service
        
        service = get_model_capabilities_service()
        return service.is_model_multimodal(model_id, api_key=self._api_key)
    
    # Methods
    def add_model(self, model: str) -> None:
        """Add a model to the list."""
        if model and model not in self._models:
            self._models.append(model)
            self.settings_changed.emit()
    
    def add_embedding_model(self, model: str) -> None:
        """Add an embedding model to the list."""
        if model and model not in self._rag_embedding_models:
            self._rag_embedding_models.append(model)
            self.settings_changed.emit()
            self.rag_settings_changed.emit()

    def remove_model(self, model: str) -> bool:
        """Remove a model from the list.
        
        Returns:
            True if removed, False if not found or last model.
        """
        if model in self._models and len(self._models) > 1:
            self._models.remove(model)
            if self._default_model == model:
                self._default_model = self._models[0]
            self.settings_changed.emit()
            return True
            self.settings_changed.emit()
            return True
        return False
    
    def remove_embedding_model(self, model: str) -> bool:
        """Remove an embedding model from the list.
        
        Returns:
            True if removed, False if not found or last model.
        """
        if model in self._rag_embedding_models and len(self._rag_embedding_models) > 1:
            self._rag_embedding_models.remove(model)
            if self._rag_embedding_model == model:
                self._rag_embedding_model = self._rag_embedding_models[0]
            self.settings_changed.emit()
            self.rag_settings_changed.emit()
            return True
        return False
    
    def update_shortcut(self, action: str, key_sequence: str) -> None:
        """Update a shortcut binding."""
        for shortcut in self._shortcuts:
            if shortcut.action == action:
                shortcut.key_sequence = key_sequence
                self.settings_changed.emit()
                return
    
    def reset_shortcuts(self) -> None:
        """Reset all shortcuts to their default values."""
        self._shortcuts = ShortcutBinding.default_shortcuts()
        self.settings_changed.emit()

    @staticmethod
    def _merge_shortcuts(
        defaults: list[ShortcutBinding],
        stored: list[ShortcutBinding],
    ) -> list[ShortcutBinding]:
        """Merge stored shortcuts with defaults, keeping new actions visible."""
        stored_map = {shortcut.action: shortcut for shortcut in stored}
        merged: list[ShortcutBinding] = []

        for default in defaults:
            stored_shortcut = stored_map.pop(default.action, None)
            if stored_shortcut:
                merged.append(
                    ShortcutBinding(
                        default.action,
                        stored_shortcut.key_sequence,
                        default.description,
                    )
                )
            else:
                merged.append(default)

        # Preserve any legacy/custom actions that no longer exist in defaults.
        merged.extend(stored_map.values())
        return merged
    
    @Slot()
    def load_settings(self) -> None:
        """Load settings from storage."""
        try:
            # Theme settings
            mode_str = self._settings_repo.get_value(self.KEY_THEME_MODE, "dark")
            self._theme_mode = ThemeMode(mode_str) if mode_str in ("light", "dark") else ThemeMode.DARK
            
            self._font_family = self._settings_repo.get_value(self.KEY_FONT_FAMILY, "Segoe UI")
            
            transparency_str = self._settings_repo.get_value(self.KEY_TRANSPARENCY, "100")
            self._transparency = max(30, min(100, int(transparency_str)))
            
            keep_above_str = self._settings_repo.get_value(self.KEY_KEEP_ABOVE, "false")
            self._keep_above = keep_above_str.lower() == "true"
            
            # Model settings
            self._default_model = self._settings_repo.get_value(
                self.KEY_DEFAULT_MODEL, DEFAULT_MODELS[0]
            )
            
            models_json = self._settings_repo.get_value(self.KEY_MODEL_LIST, "")
            if models_json:
                try:
                    self._models = json.loads(models_json)
                except json.JSONDecodeError:
                    self._models = DEFAULT_MODELS.copy()
            else:
                self._models = DEFAULT_MODELS.copy()
            
            # Load API key from keyring
            stored_key = self._keyring_service.get_api_key()
            if stored_key:
                self._api_key = stored_key
            
            # Shortcuts
            shortcuts_json = self._settings_repo.get_value(self.KEY_SHORTCUTS, "")
            default_shortcuts = ShortcutBinding.default_shortcuts()
            if shortcuts_json:
                try:
                    shortcuts_data = json.loads(shortcuts_json)
                    stored_shortcuts = [
                        ShortcutBinding(s["action"], s["key_sequence"], s["description"])
                        for s in shortcuts_data
                    ]
                    self._shortcuts = self._merge_shortcuts(
                        default_shortcuts,
                        stored_shortcuts,
                    )
                except (json.JSONDecodeError, KeyError):
                    self._shortcuts = default_shortcuts
            else:
                self._shortcuts = default_shortcuts

            memory_tokens_str = self._settings_repo.get_value(
                self.KEY_MAX_WORKSPACE_MEMORY_TOKENS, "1500"
            )
            try:
                self._max_workspace_memory_tokens = max(0, int(memory_tokens_str))
            except ValueError:
                self._max_workspace_memory_tokens = 1500

            auto_summarize_str = self._settings_repo.get_value(
                self.KEY_MEMORY_AUTO_SUMMARIZE, "true"
            )
            self._auto_summarize = auto_summarize_str.lower() in (
                "1",
                "true",
                "yes",
                "on",
            )
            
            # RAG settings
            from pathlib import Path
            default_kb = str(Path.home() / "Documents" / "Doc_RAG")
            self._rag_knowledge_base_path = self._settings_repo.get_value(
                self.KEY_RAG_KNOWLEDGE_BASE_PATH, default_kb
            )
            rag_chunk_str = self._settings_repo.get_value(self.KEY_RAG_CHUNK_SIZE, "1000")
            try:
                self._rag_chunk_size = max(100, min(10000, int(rag_chunk_str)))
            except ValueError:
                self._rag_chunk_size = 1000
            rag_overlap_str = self._settings_repo.get_value(self.KEY_RAG_CHUNK_OVERLAP, "200")
            try:
                self._rag_chunk_overlap = max(0, min(self._rag_chunk_size // 2, int(rag_overlap_str)))
            except ValueError:
                self._rag_chunk_overlap = 200
            rag_top_k_str = self._settings_repo.get_value(self.KEY_RAG_TOP_K, "4")
            try:
                self._rag_top_k = max(1, min(20, int(rag_top_k_str)))
            except ValueError:
                self._rag_top_k = 4
            self._rag_embedding_model = self._settings_repo.get_value(
                self.KEY_RAG_EMBEDDING_MODEL, "openai/text-embedding-3-small"
            )
            rag_batch_str = self._settings_repo.get_value(self.KEY_RAG_EMBEDDING_BATCH_SIZE, "20")
            try:
                self._rag_embedding_batch_size = max(1, min(100, int(rag_batch_str)))
            except ValueError:
                self._rag_embedding_batch_size = 20
            
            rag_embedding_models_json = self._settings_repo.get_value(self.KEY_RAG_EMBEDDING_MODEL_LIST, "")
            if rag_embedding_models_json:
                try:
                    self._rag_embedding_models = json.loads(rag_embedding_models_json)
                except json.JSONDecodeError:
                    self._rag_embedding_models = DEFAULT_EMBEDDING_MODELS.copy()
            else:
                self._rag_embedding_models = DEFAULT_EMBEDDING_MODELS.copy()
            
            # Capture settings
            default_capture_path = str(Path.home() / "Documents" / "temp_Attractor_Desk")
            self._capture_storage_path = self._settings_repo.get_value(
                self.KEY_CAPTURE_STORAGE_PATH, default_capture_path
            )
            capture_retention_str = self._settings_repo.get_value(
                self.KEY_CAPTURE_RETENTION_DAYS, "30"
            )
            try:
                self._capture_retention_days = max(1, min(365, int(capture_retention_str)))
            except ValueError:
                self._capture_retention_days = 30
            self._capture_last_cleanup = self._settings_repo.get_value(
                self.KEY_CAPTURE_LAST_CLEANUP, ""
            )
                
        except Exception as e:
            self.error_occurred.emit(f"Failed to load settings: {e}")
    
    @Slot()
    def save_settings(self) -> None:
        """Save settings to storage."""
        try:
            # Theme settings
            self._settings_repo.set(self.KEY_THEME_MODE, self._theme_mode.value, "theme")
            self._settings_repo.set(self.KEY_FONT_FAMILY, self._font_family, "theme")
            self._settings_repo.set(self.KEY_TRANSPARENCY, str(self._transparency), "theme")
            self._settings_repo.set(self.KEY_KEEP_ABOVE, str(self._keep_above).lower(), "theme")
            
            # Model settings
            self._settings_repo.set(self.KEY_DEFAULT_MODEL, self._default_model, "models")
            self._settings_repo.set(self.KEY_MODEL_LIST, json.dumps(self._models), "models")
            
            # Save API key to keyring
            if self._api_key:
                self._keyring_service.store_api_key(self._api_key)
            
            # Shortcuts
            shortcuts_data = [
                {"action": s.action, "key_sequence": s.key_sequence, "description": s.description}
                for s in self._shortcuts
            ]
            self._settings_repo.set(self.KEY_SHORTCUTS, json.dumps(shortcuts_data), "shortcuts")

            self._settings_repo.set(
                self.KEY_MAX_WORKSPACE_MEMORY_TOKENS,
                str(self._max_workspace_memory_tokens),
                "memory",
            )
            self._settings_repo.set(
                self.KEY_MEMORY_AUTO_SUMMARIZE,
                str(self._auto_summarize).lower(),
                "memory",
            )
            
            # RAG settings
            self._settings_repo.set(
                self.KEY_RAG_KNOWLEDGE_BASE_PATH,
                self._rag_knowledge_base_path,
                "rag",
            )
            self._settings_repo.set(
                self.KEY_RAG_CHUNK_SIZE,
                str(self._rag_chunk_size),
                "rag",
            )
            self._settings_repo.set(
                self.KEY_RAG_CHUNK_OVERLAP,
                str(self._rag_chunk_overlap),
                "rag",
            )
            self._settings_repo.set(
                self.KEY_RAG_TOP_K,
                str(self._rag_top_k),
                "rag",
            )
            self._settings_repo.set(
                self.KEY_RAG_EMBEDDING_MODEL,
                self._rag_embedding_model,
                "rag",
            )
            self._settings_repo.set(
                self.KEY_RAG_EMBEDDING_MODEL_LIST,
                json.dumps(self._rag_embedding_models),
                "rag",
            )
            self._settings_repo.set(
                self.KEY_RAG_EMBEDDING_BATCH_SIZE,
                str(self._rag_embedding_batch_size),
                "rag",
            )
            
            # Capture settings
            self._settings_repo.set(
                self.KEY_CAPTURE_STORAGE_PATH,
                self._capture_storage_path,
                "capture",
            )
            self._settings_repo.set(
                self.KEY_CAPTURE_RETENTION_DAYS,
                str(self._capture_retention_days),
                "capture",
            )
            if self._capture_last_cleanup:
                self._settings_repo.set(
                    self.KEY_CAPTURE_LAST_CLEANUP,
                    self._capture_last_cleanup,
                    "capture",
                )
            
            self.theme_changed.emit(self._theme_mode)
            self.settings_saved.emit()
            
        except Exception as e:
            self.error_occurred.emit(f"Failed to save settings: {e}")
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to defaults."""
        self._theme_mode = ThemeMode.DARK
        self._font_family = "Segoe UI"
        self._transparency = 100
        self._keep_above = False
        self._default_model = DEFAULT_MODELS[0]
        self._models = DEFAULT_MODELS.copy()
        self._shortcuts = ShortcutBinding.default_shortcuts()
        self._max_workspace_memory_tokens = 1500
        self._auto_summarize = True
        # RAG settings
        from pathlib import Path
        self._rag_knowledge_base_path = str(Path.home() / "Documents" / "Doc_RAG")
        self._rag_chunk_size = 1000
        self._rag_chunk_overlap = 200
        self._rag_top_k = 4
        self._rag_top_k = 4
        self._rag_embedding_model = "openai/text-embedding-3-small"
        self._rag_embedding_models = DEFAULT_EMBEDDING_MODELS.copy()
        self._rag_embedding_batch_size = 20
        # Capture settings
        from pathlib import Path
        self._capture_storage_path = str(Path.home() / "Documents" / "temp_Attractor_Desk")
        self._capture_retention_days = 30
        self._capture_last_cleanup = ""
        self.settings_changed.emit()
        self.rag_settings_changed.emit()
