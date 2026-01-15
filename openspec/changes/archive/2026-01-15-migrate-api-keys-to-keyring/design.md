# Design: Migrate API Keys to System Keyring

## Context
The application currently stores sensitive API keys (OpenRouter, Exa, Firecrawl, LangSmith) in a plaintext `API_KEY.txt` file at the project root. This poses security risks:
- Credentials can be accidentally committed to version control
- Any process with filesystem access can read secrets
- No OS-level protection for sensitive data

The Python `keyring` library provides a cross-platform interface to OS credential stores, offering encrypted, user-scoped secret storage.

## Goals / Non-Goals

**Goals:**
- Store all API keys in the OS keyring for secure, encrypted storage
- Support all platforms: Linux (Secret Service), macOS (Keychain), Windows (Credential Locker)
- Provide seamless migration from existing `API_KEY.txt` files
- Maintain environment variable fallback for CI/CD pipelines
- Keep keyring unavailable scenarios graceful (e.g., warn and use in-memory only)

**Non-Goals:**
- Custom encryption layer (rely on OS-provided security)
- Multi-user/team credential sharing
- Cloud-based secret management (Vault, AWS Secrets Manager)

## Architectural Decisions

### Decision 1: Centralized KeyringService
**What**: Create a single `KeyringService` class in `core/infrastructure/keyring_service.py` to manage all credential operations.

**Why**: 
- Single point of responsibility for credential access
- Easy to mock/stub in tests
- Consistent error handling

**Alternatives considered**:
1. Inline `keyring` calls in each consumer – Rejected: code duplication, inconsistent error handling
2. Store in SQLite settings table (encrypted) – Rejected: custom encryption is error-prone

### Decision 2: Multi-Key Support
**What**: The `KeyringService` will support multiple named credentials (OpenRouter, Exa, Firecrawl, LangSmith) under a single service name (`attractor_desk`).

**Why**: All keys share the same security context and lifecycle.

### Decision 3: Fallback Chain
**What**: Key retrieval follows this priority:
1. OS keyring (secure)
2. Environment variable (for CI/CD)
3. Legacy `API_KEY.txt` file (migration only, emit deprecation warning)

**Why**: Supports migration without breaking existing workflows.

### Decision 4: Migration Flow
**What**: On application startup, if `API_KEY.txt` exists and keyring has no stored keys:
1. Import keys from file to keyring
2. Show one-time prompt: "API keys migrated to secure storage. You may delete API_KEY.txt."
3. Continue using keyring for all subsequent accesses

**Why**: Zero-friction migration for existing users.

### Decision 5: SettingsViewModel Integration
**What**: `SettingsViewModel` will inject `KeyringService` and use it to load/save the API key. The stored value in SQLite will be a flag indicating "use keyring" rather than the actual secret.

**Why**: Keeps secrets out of SQLite; SQLite only stores non-sensitive settings.

## Component Design

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Application Layer                              │
│  ┌──────────────┐   ┌───────────────────┐   ┌─────────────────────────┐ │
│  │SettingsVM    │   │OpenRouterChat     │   │ExaSearchProvider        │ │
│  │              │   │Embeddings         │   │FireCrawlProvider        │ │
│  └──────┬───────┘   └─────────┬─────────┘   └───────────┬─────────────┘ │
│         │                     │                         │               │
│         └─────────────────────┼─────────────────────────┘               │
│                               ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                      KeyringService                                  ││
│  │  store_credential(name, value)                                       ││
│  │  get_credential(name) → Optional[str]                                ││
│  │  delete_credential(name)                                             ││
│  │  has_credential(name) → bool                                         ││
│  │  migrate_from_file() → dict[str, bool]                               ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                               │                                          │
└───────────────────────────────┼──────────────────────────────────────────┘
                                ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │                   OS Credential Backend                              │
    │  Linux: Secret Service (GNOME Keyring / KWallet)                    │
    │  macOS: Keychain                                                    │
    │  Windows: Credential Locker                                         │
    └─────────────────────────────────────────────────────────────────────┘
```

## KeyringService Interface

```python
class KeyringService:
    """Secure credential storage using OS keyring."""
    
    SERVICE_NAME = "attractor_desk"
    
    CREDENTIAL_NAMES = {
        "openrouter": "openrouter_api_key",
        "exa": "exa_api_key",
        "firecrawl": "firecrawl_api_key",
        "langsmith": "langsmith_api_key",
    }
    
    def __init__(self) -> None: ...
    
    @property
    def is_available(self) -> bool: ...
    
    def store_credential(self, name: str, value: str) -> bool: ...
    def get_credential(self, name: str) -> Optional[str]: ...
    def delete_credential(self, name: str) -> bool: ...
    def has_credential(self, name: str) -> bool: ...
    
    def migrate_from_file(self, file_path: Path) -> dict[str, bool]: ...
```

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| Keyring unavailable on headless Linux | Keys cannot be stored | Warn user; fallback to env vars; suggest `keyrings.alt` |
| User deletes keyring entry | API key lost | Document recovery via settings UI |
| CI/CD environments lack keyring | Build/test failures | Document env var override |
| Migration deletes file prematurely | Key loss | Never auto-delete; prompt user |

## Migration Plan

1. **Phase 1**: Add `keyring` dependency and `KeyringService` module
2. **Phase 2**: Refactor `core/config.py` with keyring-first lookup
3. **Phase 3**: Update `SettingsViewModel` to use `KeyringService`
4. **Phase 4**: Update settings UI to prompt for migration
5. **Phase 5**: Update provider classes to use new config functions
6. **Phase 6**: Update documentation (README, API_KEY.txt.example → deprecate)
7. **Phase 7**: Remove `API_KEY.txt` logic in a future release (gated by config flag)

**Rollback**: Restore `API_KEY.txt` handling in `core/config.py` and revert SettingsViewModel changes. Keyring entries remain but are ignored.

## Open Questions

1. Should the migration prompt block app startup or show as a dismissable notification?
   - **Proposed**: Non-blocking notification in the settings area on first launch.
   
2. Should we support exporting credentials back to a file for backup?
   - **Proposed**: Defer to future release; users can use OS keyring management tools.
