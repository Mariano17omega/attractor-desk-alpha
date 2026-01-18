# ViewModel Refactoring Plan

**Project:** Attractor Desk (v0.3.0 Alpha)
**Analysis Date:** 2026-01-17
**Scope:** SettingsViewModel God Object Refactoring
**Status:** Planning Phase

---

## Executive Summary

The `SettingsViewModel` class has grown to **1148 lines**, violating the Single Responsibility Principle. It manages 10 distinct domains: appearance, models, deep search, RAG configuration, global RAG operations, ChatPDF cleanup, shortcuts, UI visibility, persistence, and API key migration.

**Recommended Action:** Extract into 9 focused classes orchestrated by a `SettingsCoordinator` facade.

---

## Current Architecture Analysis

### File Location
- **Primary File:** `ui/viewmodels/settings_viewmodel.py` (1148 lines)
- **Related Issue:** CODE_REVIEW.md Line 159-196

### Complexity Metrics
- **Properties/Setters**: 45
- **Business Logic Methods**: 15
- **Qt Signals**: 12
- **Constants/Defaults**: 3 groups
- **Cognitive Load**: Very High

---

## 1. Methods Grouped by Responsibility

### A. Appearance/Theme Management (Lines 213-260)
**Scope:** UI theming, fonts, transparency, window behavior

**Methods:**
- `theme_mode` property + setter (lines 213-226)
- `font_family` property + setter (lines 228-236)
- `transparency` property + setter (lines 238-248)
- `keep_above` property + setter (lines 250-259)

**Signals:**
- `theme_changed`
- `transparency_changed`
- `keep_above_changed`

**Dependencies:** Persistence layer only

---

### B. Model Configuration Management (Lines 261-323)
**Scope:** LLM model selection, API key management

**Methods:**
- `keyring_available` property (lines 261-264)
- `has_openrouter_key` property (lines 266-269)
- `api_key` property + setter (lines 271-280)
- `default_model` property + setter (lines 282-290)
- `image_model` property + setter (lines 292-300)
- `models` property + `add_model()` (lines 302-311)
- `image_models` property + `add_image_model()` (lines 313-322)

**Constants:**
- `DEFAULT_MODELS` (lines 23-36)
- `DEFAULT_IMAGE_MODELS` (lines 38-47)

**Dependencies:** Persistence + KeyringService

---

### C. Deep Search Configuration (Lines 324-378)
**Scope:** Exa/Firecrawl web search settings

**Methods:**
- `deep_search_enabled` property + setter (lines 324-334)
- `exa_api_key` property + setter (lines 336-345)
- `firecrawl_api_key` property + setter (lines 358-367)
- `search_provider` property + setter (lines 369-378)
- `deep_search_num_results` property + setter (lines 347-356)

**Signals:**
- `deep_search_toggled`

**Dependencies:** Persistence + KeyringService

---

### D. RAG Configuration (Lines 380-553)
**Scope:** RAG algorithm parameters, folder paths, feature flags

**Methods:**
- `rag_enabled` property + setter (lines 380-389)
- `rag_scope` property + setter (lines 391-400)
- `rag_chunk_size_chars` property + setter (lines 402-413)
- `rag_chunk_overlap_chars` property + setter (lines 415-426)
- `rag_k_lex` property + setter (lines 428-437)
- `rag_k_vec` property + setter (lines 439-448)
- `rag_rrf_k` property + setter (lines 450-459)
- `rag_max_candidates` property + setter (lines 461-470)
- `rag_embedding_model` property + setter (lines 472-481)
- `rag_enable_query_rewrite` property + setter (lines 483-492)
- `rag_enable_llm_rerank` property + setter (lines 494-503)
- `rag_index_text_artifacts` property + setter (lines 505-514)
- `rag_global_folder` property + setter (lines 516-527) ⚠️ **Triggers monitoring**
- `rag_global_monitoring_enabled` property + setter (lines 529-542) ⚠️ **Controls watcher service**
- `rag_chatpdf_retention_days` property + setter (lines 544-553)

**Dependencies:** Persistence layer

**⚠️ Critical Side Effects:**
- `rag_global_folder` setter calls `_start_global_monitoring()` (line 527)
- `rag_global_monitoring_enabled` setter controls `PdfWatcherService` (lines 540-542)

---

### E. Global RAG Operations (Lines 1023-1088)
**Scope:** Background indexing, PDF monitoring, registry management

**Methods:**
- `start_global_index()` (lines 1023-1028)
- `scan_global_folder()` (lines 1030-1035)
- `list_global_registry_entries()` (lines 1037-1038)
- `get_global_registry_status_counts()` (lines 1040-1041)
- `_build_global_request()` (lines 1043-1053)
- `_start_global_monitoring()` (lines 1055-1059)
- `_on_global_pdfs_detected()` (lines 1061-1076)
- `_on_global_index_progress()` (lines 1078-1079)
- `_on_global_index_complete()` (lines 1081-1083)
- `_on_global_index_error()` (lines 1085-1087)

**Signals:**
- `global_rag_progress`
- `global_rag_complete`
- `global_rag_error`
- `global_rag_registry_updated`

**Dependencies:**
- RAG Configuration (reads settings)
- Model Configuration (reads `api_key`)
- `GlobalRagService`
- `PdfWatcherService`
- `RagRepository`

---

### F. ChatPDF Cleanup Operations (Lines 1089-1116)
**Scope:** Stale ChatPDF document deletion

**Methods:**
- `cleanup_chatpdf_documents()` (lines 1089-1092)
- `_run_chatpdf_cleanup()` (lines 1094-1116)

**Signals:**
- `chatpdf_cleanup_complete`

**QTimer:** Runs every 24 hours (lines 207-210)

**Dependencies:**
- RAG Configuration (reads `rag_chatpdf_retention_days`)
- `RagRepository`
- `ChromaService` (optional)

---

### G. Keyboard Shortcuts Management (Lines 555-578)
**Scope:** Customizable keyboard shortcuts

**Methods:**
- `shortcut_definitions` property (lines 555-557)
- `shortcut_bindings` property (lines 559-561)
- `get_shortcut_sequence()` (lines 563-564)
- `set_shortcut_sequence()` (lines 566-573)
- `reset_shortcuts()` (lines 575-578)
- `_normalize_shortcut_bindings()` (lines 602-612)

**Constants:**
- `DEFAULT_SHORTCUT_DEFINITIONS` (lines 49-92)
- `DEFAULT_SHORTCUT_BINDINGS` (lines 94-97)

**Signals:**
- `shortcuts_changed`

**Dependencies:** Persistence layer only

---

### H. UI Visibility State (Lines 580-600)
**Scope:** Sidebar/artifact panel visibility persistence

**Methods:**
- `sidebar_visible` property + setter (lines 580-589)
- `artifact_panel_visible` property + setter (lines 591-600)

**Dependencies:** Persistence layer only

---

### I. Persistence Layer (Lines 710-1022)
**Scope:** SQLite + keyring persistence

**Methods:**
- `load_settings()` (lines 710-831) - **265 lines!**
- `save_settings()` (lines 833-1017) - **184 lines!**
- `snapshot()` (lines 614-646)
- `restore_snapshot()` (lines 648-708)
- `revert_to_saved()` (lines 1019-1021)

**Signals:**
- `settings_changed`
- `settings_saved`
- `error_occurred`

**Dependencies:** All other groups

---

### J. API Key Migration (Lines 1118-1147)
**Scope:** Migrate legacy `API_KEY.txt` to keyring

**Methods:**
- `migrate_legacy_keys()` (lines 1118-1147)

**Signals:**
- `keys_migrated`

**Dependencies:** KeyringService + Persistence layer

---

## 2. Dependencies Between Groups

```
A. Appearance
   └─> I. Persistence (read/write theme settings)

B. Model Configuration
   ├─> I. Persistence (read/write model settings + API keys)
   └─> KeyringService (API key storage)

C. Deep Search
   ├─> I. Persistence (read/write search settings)
   └─> KeyringService (API key storage)

D. RAG Configuration
   ├─> I. Persistence (read/write RAG settings)
   ├─> E. Global RAG Operations (rag_global_folder setter triggers monitoring)
   └─> E. Global RAG Operations (rag_global_monitoring_enabled setter)

E. Global RAG Operations
   ├─> D. RAG Configuration (reads RAG settings to build requests)
   ├─> B. Model Configuration (reads api_key for embeddings)
   ├─> GlobalRagService (orchestrates indexing)
   ├─> PdfWatcherService (monitors folder for new PDFs)
   └─> RagRepository (database access)

F. ChatPDF Cleanup
   ├─> D. RAG Configuration (reads retention days)
   ├─> RagRepository (database access)
   └─> ChromaService (optional vector DB cleanup)

G. Shortcuts
   └─> I. Persistence (read/write shortcuts)

H. UI Visibility
   └─> I. Persistence (read/write visibility state)

J. API Key Migration
   ├─> KeyringService (migrate to keyring)
   └─> I. Persistence (reload after migration)
```

**Critical Dependencies:**
- **E (Global RAG) ← D (RAG Config)**: Setters in D trigger operations in E
- **F (ChatPDF Cleanup) → D + RagRepository + ChromaService**: Multi-service dependency
- **All groups → I (Persistence)**: Everything depends on load/save

---

## 3. Safest Order to Extract Classes

### Phase 1: Low-Risk Extractions
**Timeline:** 1-2 days

#### 1.1 Extract AppearanceSettings
- **Complexity:** ⭐ Low
- **Dependencies:** Only persistence layer
- **Impact:** 1 UI file (`ui/widgets/configuration/theme_page.py`)
- **Risk:** Very low - no side effects in setters
- **Signals to forward:** `theme_changed`, `transparency_changed`, `keep_above_changed`

#### 1.2 Extract ShortcutsSettings
- **Complexity:** ⭐ Low
- **Dependencies:** Only persistence layer + static defaults
- **Impact:** 2 UI files (`ui/widgets/configuration/shortcuts_page.py`, `ui/main_window.py`)
- **Risk:** Very low - pure data management
- **Signals to forward:** `shortcuts_changed`

#### 1.3 Extract UIVisibilitySettings
- **Complexity:** ⭐ Low
- **Dependencies:** Only persistence layer
- **Impact:** 1 UI file (`ui/main_window.py` for sidebar/artifact panel)
- **Risk:** Very low - trivial properties
- **Signals to forward:** None (uses `settings_changed` from persistence)

---

### Phase 2: Medium-Risk Extractions
**Timeline:** 2-3 days

#### 2.1 Extract ModelSettings
- **Complexity:** ⭐⭐ Medium
- **Dependencies:** Persistence + KeyringService
- **Impact:** 2 UI files (`ui/widgets/configuration/models_page.py`, `ui/main_window.py` for capture logic)
- **Risk:** Medium - KeyringService must be injected properly
- **Signals to forward:** `settings_changed`

#### 2.2 Extract DeepSearchSettings
- **Complexity:** ⭐⭐ Medium
- **Dependencies:** Persistence + KeyringService
- **Impact:** 2 UI files (`ui/widgets/configuration/deep_search_page.py`, `ui/main_window.py`)
- **Risk:** Medium - KeyringService must be injected properly
- **Signals to forward:** `deep_search_toggled`, `settings_changed`

---

### Phase 3: High-Risk Extractions
**Timeline:** 5-7 days

#### 3.1 Extract RAGConfigurationSettings (Configuration ONLY)
- **Complexity:** ⭐⭐⭐ High
- **Dependencies:** Persistence layer
- **Scope:** All RAG properties EXCEPT folder monitoring/indexing triggers
- **Impact:** 1 UI file (`ui/widgets/configuration/rag_page.py`)
- **Risk:** Medium-High - Must not include operations
- **Signals to forward:** `settings_changed`

#### 3.2 Extract GlobalRAGOrchestrator
- **Complexity:** ⭐⭐⭐⭐ Very High
- **Dependencies:** RAGConfigurationSettings + GlobalRagService + PdfWatcherService + RagRepository + ModelSettings
- **Scope:** All indexing, monitoring, and registry operations
- **Impact:** 1 UI file (`ui/widgets/configuration/rag_page.py` for indexing UI)
- **Risk:** **High** - Critical to preserve signal connections
- **Signals to forward:** `global_rag_progress`, `global_rag_complete`, `global_rag_error`, `global_rag_registry_updated`

#### 3.3 Extract ChatPDFCleanupService
- **Complexity:** ⭐⭐⭐ High
- **Dependencies:** RAGConfigurationSettings + RagRepository + ChromaService
- **Scope:** Cleanup operations + QTimer
- **Impact:** 1 UI file (`ui/widgets/configuration/rag_page.py` if cleanup UI exists)
- **Risk:** Medium-High - QTimer lifecycle must be managed correctly
- **Signals to forward:** `chatpdf_cleanup_complete`

---

### Phase 4: Refactor Persistence
**Timeline:** 2-3 days

#### 4.1 Extract SettingsPersistenceService
- **Complexity:** ⭐⭐⭐⭐ Very High
- **Dependencies:** SettingsRepository + all extracted settings classes
- **Scope:** Centralized load_settings() / save_settings()
- **Impact:** All UI files indirectly (settings save flow)
- **Risk:** **Very High** - Refactor after all extractions complete
- **Signals to forward:** `settings_saved`, `error_occurred`

#### 4.2 Extract APIKeyMigrationService
- **Complexity:** ⭐⭐ Medium
- **Dependencies:** KeyringService + SettingsPersistenceService
- **Scope:** migrate_legacy_keys()
- **Impact:** No UI files (only called at startup)
- **Risk:** Low - One-time operation
- **Signals to forward:** `keys_migrated`

---

## 4. UI Files Requiring Updates

| UI File | Affected by Phase | Required Changes |
|---------|------------------|------------------|
| **ui/widgets/configuration/theme_page.py** | Phase 1.1 | Import `AppearanceSettings`, access via `settings.appearance.*` |
| **ui/widgets/configuration/shortcuts_page.py** | Phase 1.2 | Import `ShortcutsSettings`, access via `settings.shortcuts.*` |
| **ui/main_window.py** | Phases 1.2, 1.3, 2.1, 2.2 | Update signal connections, access nested settings objects |
| **ui/widgets/configuration/models_page.py** | Phase 2.1 | Import `ModelSettings`, access via `settings.models.*` |
| **ui/widgets/configuration/deep_search_page.py** | Phase 2.2 | Import `DeepSearchSettings`, access via `settings.deep_search.*` |
| **ui/widgets/configuration/rag_page.py** | Phases 3.1, 3.2, 3.3 | Import `RAGConfigurationSettings` + `GlobalRAGOrchestrator` + `ChatPDFCleanupService` |
| **ui/widgets/configuration/configuration_dialog.py** | All phases | Update constructor to pass `SettingsCoordinator` to child pages |

---

## 5. Proposed Target Architecture

### File Structure
```
ui/viewmodels/settings/
├── __init__.py                        # Exports SettingsCoordinator
├── coordinator.py                     # SettingsCoordinator facade
├── appearance_settings.py             # Theme, fonts, transparency
├── shortcuts_settings.py              # Keyboard shortcuts
├── ui_visibility_settings.py          # Panel visibility
├── model_settings.py                  # LLM models, API keys
├── deep_search_settings.py            # Exa/Firecrawl
├── rag_configuration_settings.py     # RAG parameters
├── global_rag_orchestrator.py         # Global RAG indexing
├── chatpdf_cleanup_service.py         # ChatPDF cleanup
├── persistence_service.py             # Centralized load/save
└── api_key_migration_service.py       # Legacy key migration
```

### SettingsCoordinator Facade

```python
# ui/viewmodels/settings/coordinator.py
from __future__ import annotations

from typing import Optional
from PySide6.QtCore import QObject, Signal

from core.persistence import Database
from core.infrastructure.keyring_service import KeyringService, get_keyring_service
from core.services.chroma_service import ChromaService

from .appearance_settings import AppearanceSettings
from .shortcuts_settings import ShortcutsSettings
from .ui_visibility_settings import UIVisibilitySettings
from .model_settings import ModelSettings
from .deep_search_settings import DeepSearchSettings
from .rag_configuration_settings import RAGConfigurationSettings
from .global_rag_orchestrator import GlobalRAGOrchestrator
from .chatpdf_cleanup_service import ChatPDFCleanupService
from .persistence_service import SettingsPersistenceService
from .api_key_migration_service import APIKeyMigrationService


class SettingsCoordinator(QObject):
    """Facade coordinating all settings subsystems."""

    # Forwarded signals
    settings_saved = Signal()
    error_occurred = Signal(str)
    keys_migrated = Signal(dict)

    def __init__(
        self,
        settings_db: Optional[Database] = None,
        keyring_service: Optional[KeyringService] = None,
        chroma_service: Optional[ChromaService] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)

        # Shared dependencies
        self._db = settings_db or Database()
        self._keyring = keyring_service or get_keyring_service()
        self._chroma = chroma_service

        # Simple settings subsystems
        self.appearance = AppearanceSettings(self._db)
        self.shortcuts = ShortcutsSettings(self._db)
        self.ui_visibility = UIVisibilitySettings(self._db)
        self.models = ModelSettings(self._db, self._keyring)
        self.deep_search = DeepSearchSettings(self._db, self._keyring)
        self.rag_config = RAGConfigurationSettings(self._db)

        # Complex orchestrators
        self.global_rag = GlobalRAGOrchestrator(
            config=self.rag_config,
            models=self.models,
            db=self._db,
            chroma_service=self._chroma,
            parent=self,
        )

        self.chatpdf_cleanup = ChatPDFCleanupService(
            config=self.rag_config,
            db=self._db,
            chroma_service=self._chroma,
            parent=self,
        )

        # Persistence coordinator
        self.persistence = SettingsPersistenceService(
            db=self._db,
            subsystems=[
                self.appearance,
                self.shortcuts,
                self.ui_visibility,
                self.models,
                self.deep_search,
                self.rag_config,
            ],
        )

        # Migration service
        self.migration = APIKeyMigrationService(
            keyring=self._keyring,
            persistence=self.persistence,
        )

        # Wire up signals
        self._connect_signals()

    def _connect_signals(self) -> None:
        """Forward signals from subsystems."""
        self.persistence.settings_saved.connect(self.settings_saved)
        self.persistence.error_occurred.connect(self.error_occurred)
        self.migration.keys_migrated.connect(self.keys_migrated)

    def load_settings(self) -> None:
        """Load all settings from persistence."""
        self.persistence.load_all()

    def save_settings(self) -> None:
        """Save all settings to persistence."""
        self.persistence.save_all()

    def revert_to_saved(self) -> None:
        """Restore all settings to last saved state."""
        self.persistence.revert_all()

    def migrate_legacy_keys(self, legacy_file_path=None) -> dict[str, bool]:
        """Migrate API keys from legacy API_KEY.txt to keyring."""
        return self.migration.migrate_from_file(legacy_file_path)
```

---

## 6. Critical Risks & Mitigation

### ⚠️ Risk 1: RAG Folder Monitoring Side Effects
**Location:** `ui/viewmodels/settings_viewmodel.py:520-527`

**Issue:**
```python
@rag_global_folder.setter
def rag_global_folder(self, value: str) -> None:
    # ... validation
    if self._rag_global_monitoring_enabled:
        self._start_global_monitoring()  # SIDE EFFECT!
```

**Mitigation:**
- Move side effect out of setter into `GlobalRAGOrchestrator`
- Create explicit `set_folder_and_restart_monitoring(folder: str)` method
- Settings dialog calls orchestrator method explicitly

---

### ⚠️ Risk 2: Signal Connection Breakage
**Location:** `ui/main_window.py:154-160`

**Issue:**
```python
self._settings_viewmodel.theme_changed.connect(self._apply_theme)
self._settings_viewmodel.transparency_changed.connect(self._apply_transparency)
# ... 5 more connections
```

**Mitigation:**
- Use signal forwarding in `SettingsCoordinator`
- Forward all subsystem signals through coordinator:
  ```python
  self.appearance.theme_changed.connect(self.theme_changed)
  ```
- UI code connects to coordinator, not subsystems

---

### ⚠️ Risk 3: QTimer Lifecycle in ChatPDF Cleanup
**Location:** `ui/viewmodels/settings_viewmodel.py:207-210`

**Issue:**
```python
self._cleanup_timer = QTimer(self)
self._cleanup_timer.setInterval(24 * 60 * 60 * 1000)
self._cleanup_timer.timeout.connect(self._run_chatpdf_cleanup)
self._cleanup_timer.start()
```

**Mitigation:**
- Move timer to `ChatPDFCleanupService` with proper parent
- Ensure service is deleted when coordinator is deleted
- Add explicit `start()` / `stop()` lifecycle methods

---

### ⚠️ Risk 4: Circular Dependencies
**Issue:** `GlobalRAGOrchestrator` needs `RAGConfigurationSettings` + `ModelSettings`

**Mitigation:**
- Use dependency injection everywhere
- Subsystems NEVER import coordinator
- Coordinator imports all subsystems (one-way dependency)
- Pass specific subsystems to orchestrators, not entire coordinator

---

### ⚠️ Risk 5: Persistence Load Order
**Issue:** Settings may depend on each other during load (e.g., RAG folder path before monitoring)

**Mitigation:**
- Load settings in two phases:
  1. **Phase 1**: Load all simple settings (values only)
  2. **Phase 2**: Initialize orchestrators (side effects allowed)
- Document load order in `SettingsPersistenceService`

---

## 7. Testing Strategy

### Unit Tests (Per Subsystem)
```python
# tests/ui/viewmodels/settings/test_appearance_settings.py
def test_theme_mode_change_emits_signal(appearance_settings):
    with qtbot.waitSignal(appearance_settings.theme_changed):
        appearance_settings.theme_mode = ThemeMode.LIGHT

def test_transparency_clamped_to_range(appearance_settings):
    appearance_settings.transparency = 150
    assert appearance_settings.transparency == 100  # Clamped to max

def test_transparency_persisted_to_database(appearance_settings, db_repo):
    appearance_settings.transparency = 85
    appearance_settings.save()

    # Reload from DB
    new_instance = AppearanceSettings(db_repo)
    new_instance.load()
    assert new_instance.transparency == 85
```

### Integration Tests (Coordinator)
```python
# tests/ui/viewmodels/settings/test_settings_coordinator.py
def test_coordinator_load_saves_all_subsystems(coordinator, mock_db):
    coordinator.appearance.theme_mode = ThemeMode.LIGHT
    coordinator.models.default_model = "gpt-4o"
    coordinator.save_settings()

    # Verify all subsystems saved
    assert mock_db.get_value("theme.mode") == "light"
    assert mock_db.get_value("models.default") == "gpt-4o"

def test_revert_to_saved_restores_snapshot(coordinator):
    coordinator.appearance.transparency = 50
    coordinator.save_settings()

    coordinator.appearance.transparency = 80
    coordinator.revert_to_saved()

    assert coordinator.appearance.transparency == 50
```

### Regression Tests (UI)
```python
# tests/ui/widgets/test_configuration_dialog.py
def test_theme_page_updates_coordinator(qtbot, settings_coordinator):
    dialog = ConfigurationDialog(settings_coordinator)
    theme_page = dialog._theme_page

    # Simulate user changing theme
    theme_page._theme_combo.setCurrentText("Light")
    theme_page._apply_changes()

    assert settings_coordinator.appearance.theme_mode == ThemeMode.LIGHT
```

---

## 8. Migration Checklist

### Phase 1: Low-Risk Extractions
- [ ] Create `ui/viewmodels/settings/` directory
- [ ] Extract `AppearanceSettings` class
- [ ] Write unit tests for `AppearanceSettings`
- [ ] Update `theme_page.py` to use new class
- [ ] Extract `ShortcutsSettings` class
- [ ] Write unit tests for `ShortcutsSettings`
- [ ] Update `shortcuts_page.py` and `main_window.py`
- [ ] Extract `UIVisibilitySettings` class
- [ ] Write unit tests for `UIVisibilitySettings`
- [ ] Update `main_window.py` visibility toggling
- [ ] Create `SettingsCoordinator` scaffold
- [ ] Run regression tests on configuration dialog

### Phase 2: Medium-Risk Extractions
- [ ] Extract `ModelSettings` class
- [ ] Write unit tests for `ModelSettings` (including keyring)
- [ ] Update `models_page.py` and `main_window.py`
- [ ] Extract `DeepSearchSettings` class
- [ ] Write unit tests for `DeepSearchSettings`
- [ ] Update `deep_search_page.py` and `main_window.py`
- [ ] Run regression tests on search functionality

### Phase 3: High-Risk Extractions
- [ ] Extract `RAGConfigurationSettings` (config only, no operations)
- [ ] Write unit tests for `RAGConfigurationSettings`
- [ ] Extract `GlobalRAGOrchestrator`
- [ ] Move `PdfWatcherService` lifecycle to orchestrator
- [ ] Write integration tests for global RAG indexing
- [ ] Extract `ChatPDFCleanupService`
- [ ] Move `QTimer` lifecycle to cleanup service
- [ ] Write integration tests for cleanup
- [ ] Update `rag_page.py` to use new classes
- [ ] Run regression tests on RAG functionality

### Phase 4: Persistence Refactor
- [ ] Extract `SettingsPersistenceService`
- [ ] Implement two-phase load strategy
- [ ] Write integration tests for save/load/revert
- [ ] Extract `APIKeyMigrationService`
- [ ] Write unit tests for migration
- [ ] Complete `SettingsCoordinator` implementation
- [ ] Update all UI files to use coordinator
- [ ] Run full regression test suite
- [ ] Delete old `settings_viewmodel.py`
- [ ] Update documentation

### Post-Migration
- [ ] Update CODE_REVIEW.md to mark God Object issue as resolved
- [ ] Add architecture documentation to CLAUDE.md
- [ ] Create migration guide for future ViewModels (ChatViewModel)

---

## 9. Estimated Effort

| Phase | Tasks | Estimated Time | Risk Level |
|-------|-------|----------------|------------|
| Phase 1 | Low-risk extractions | 1-2 days | Low |
| Phase 2 | Medium-risk extractions | 2-3 days | Medium |
| Phase 3 | High-risk extractions | 5-7 days | High |
| Phase 4 | Persistence refactor | 2-3 days | Very High |
| **Total** | **Complete refactoring** | **10-15 days** | **Medium-High** |

---

## 10. Success Criteria

### Code Quality Metrics
- [ ] No class exceeds 300 lines
- [ ] Each class has a single, well-defined responsibility
- [ ] Cyclomatic complexity \< 10 per method
- [ ] Test coverage \> 80% for all new classes

### Functional Requirements
- [ ] All existing settings functionality preserved
- [ ] No regressions in UI behavior
- [ ] Signal connections work identically
- [ ] Persistence layer unchanged from user perspective

### Architecture Goals
- [ ] Clear separation of concerns
- [ ] Subsystems independently testable
- [ ] Dependency injection throughout
- [ ] No circular dependencies

---

## 11. Future Work

### ChatViewModel Refactoring
The `ChatViewModel` (700+ lines) also violates SRP. Apply similar extraction pattern:

**Proposed Subsystems:**
1. **SessionManagement** - Workspace/session switching
2. **MessageHandling** - Message send/receive/display
3. **GraphOrchestrator** - LangGraph execution lifecycle
4. **PDFImportService** - ChatPDF mode PDF handling
5. **RAGIndexingService** - Local RAG indexing coordination
6. **ArtifactManager** - Artifact CRUD operations
7. **AttachmentHandler** - Image attachments + screen capture

**Estimated Effort:** 15-20 days (more complex than SettingsViewModel)

---

## References

- **Original Issue:** CODE_REVIEW.md Lines 159-196
- **Current File:** `ui/viewmodels/settings_viewmodel.py`
- **UI Dependencies:** 7 files in `ui/widgets/configuration/` + `ui/main_window.py`
- **Related Services:** `GlobalRagService`, `PdfWatcherService`, `ChromaService`, `KeyringService`

---

**Last Updated:** 2026-01-17
**Status:** Ready for Implementation
