# Change: Migrate API Keys to System Keyring

## Why
The current implementation stores API keys in a plaintext `API_KEY.txt` file, creating a security risk. Sensitive credentials should be stored in the operating system's secure credential vault (keyring) to follow security best practices and prevent accidental exposure via git commits or filesystem access.

## What Changes
- **BREAKING**: Remove dependency on `API_KEY.txt` file for API key storage
- Add new `core/infrastructure/keyring_service.py` module for secure credential management
- Refactor `core/config.py` to prioritize keyring over file-based storage
- Update `SettingsViewModel` to store/retrieve API keys via the keyring service
- Migrate settings UI to use keyring for all secret fields (OpenRouter, Exa, Firecrawl, LangSmith)
- Update provider classes to retrieve keys through the new centralized keyring service
- Add migration logic to import existing keys from `API_KEY.txt` on first run (then prompt to delete)
- Support environment variable fallback for CI/CD and containerized environments
- Add `keyring` as a required dependency in `pyproject.toml`

## Impact
- Affected specs: `settings-configuration`
- Affected code:
  - `core/config.py` – refactor to use keyring as primary source
  - `core/infrastructure/keyring_service.py` – new file
  - `ui/viewmodels/settings_viewmodel.py` – integrate keyring service
  - `ui/widgets/settings_dialog.py` – remove direct config import for API keys
  - `core/providers/exa_search.py` – use keyring-aware getter
  - `core/providers/firecrawl.py` – use keyring-aware getter
  - `core/llm/openrouter.py` – use keyring-aware getter
  - `core/llm/embeddings.py` – use keyring-aware getter
  - `pyproject.toml` – add `keyring` dependency
  - `README.md` – update setup instructions
  - `API_KEY.txt.example` – deprecate or remove

## User Review Required

> [!IMPORTANT]
> **Breaking Change**: Users will need to migrate their API keys from `API_KEY.txt` to the system keyring on first run. A one-time migration prompt will be shown.

> [!IMPORTANT]  
> **Cross-Platform Behavior**: On Linux, keyring uses Secret Service (GNOME Keyring, KWallet); on macOS, Keychain; on Windows, Credential Locker. Headless/server environments may require `keyrings.alt` backend configuration.
