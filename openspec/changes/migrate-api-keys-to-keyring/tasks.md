# Tasks: Migrate API Keys to System Keyring

## 1. Add Dependency and Core Service

- [x] 1.1 Add `keyring` to `pyproject.toml` dependencies
- [x] 1.2 Create `core/infrastructure/__init__.py` if not present
- [x] 1.3 Create `core/infrastructure/keyring_service.py` with `KeyringService` class
- [x] 1.4 Implement `store_credential()`, `get_credential()`, `delete_credential()`, `has_credential()` methods
- [x] 1.5 Implement `migrate_from_file()` method to import keys from `API_KEY.txt`
- [x] 1.6 Add unit tests for `KeyringService` in `tests/test_keyring_service.py`

## 2. Refactor Configuration Module

- [x] 2.1 Refactor `core/config.py` to add keyring-first credential lookup
- [x] 2.2 Update `get_api_key()` to check keyring → env var → legacy file
- [x] 2.3 Add deprecation warning when falling back to `API_KEY.txt`
- [x] 2.4 Update `get_openrouter_api_key()`, `get_exa_api_key()`, `get_firecrawl_api_key()`, `get_langsmith_api_key()` helpers
- [x] 2.5 Update unit tests in `tests/test_config_tracing.py` to cover new fallback chain

## 3. Integrate with SettingsViewModel

- [x] 3.1 Add `KeyringService` as a dependency to `SettingsViewModel.__init__()`
- [x] 3.2 Modify `load_settings()` to load API keys from keyring
- [x] 3.3 Modify `save_settings()` to persist API keys to keyring (not SQLite)
- [x] 3.4 Add `has_openrouter_key` property that checks keyring
- [x] 3.5 Add `migrate_legacy_keys()` method to trigger one-time migration
- [x] 3.6 Add signal for migration success notification (`keys_migrated`)

## 4. Update Settings UI

- [x] 4.1 Remove direct `core/config import get_api_key` from `ui/widgets/settings_dialog.py`
- [x] 4.2 Update API key field loading to use ViewModel
- [ ] 4.3 Add migration prompt/notification in settings page (deferred - non-blocking per design)
- [x] 4.4 Show keyring status indicator (`keyring_available` property added)

## 5. Update Provider Classes

- [x] 5.1 Update `core/llm/openrouter.py` to use `get_openrouter_api_key()` (centralized) - already uses it
- [x] 5.2 Update `core/llm/embeddings.py` to use centralized getter - already uses it
- [x] 5.3 Update `core/providers/exa_search.py` to use centralized `get_exa_api_key()` - already uses it
- [x] 5.4 Update `core/providers/firecrawl.py` to use centralized `get_firecrawl_api_key()` - already uses it
- [x] 5.5 Remove direct file-reading fallback from provider classes (updated docstrings/error messages)

## 6. Update Documentation

- [x] 6.1 Update `README.md` with new setup instructions (keyring-based)
- [x] 6.2 Add migration guide section to README
- [x] 6.3 Deprecate `API_KEY.txt.example` (add deprecation notice header)
- [x] 6.4 Update `openspec/project.md` to reflect keyring-based storage
- [x] 6.5 Update `AGENTS.md` if it references `API_KEY.txt`

## 7. Verification

- [x] 7.1 Run all unit tests: `pytest tests/` - 71 passed
- [ ] 7.2 Manual test: fresh install with no `API_KEY.txt` → prompt for API key in settings → store in keyring
- [ ] 7.3 Manual test: existing `API_KEY.txt` → auto-migration to keyring → deprecation notice
- [ ] 7.4 Manual test: env var `OPENROUTER_API_KEY` overrides keyring
- [ ] 7.5 Manual test: headless environment (no keyring backend) → graceful warning

---

**Dependencies**: Task groups 1–2 can be parallelized. Group 3 depends on 1–2. Groups 4–5 depend on 3. Group 6 can start after 3. Group 7 is final.
