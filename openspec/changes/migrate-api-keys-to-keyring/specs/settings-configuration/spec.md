# settings-configuration Spec Delta

## ADDED Requirements

### Requirement: Secure API Key Storage
The system SHALL store all API keys (OpenRouter, Exa, Firecrawl, LangSmith) in the operating system's secure credential vault using the `keyring` library rather than plaintext files or SQLite.

#### Scenario: Store API key in keyring
- **WHEN** the user enters an API key in the settings dialog and saves
- **THEN** the key is securely stored in the OS keyring under the `attractor_desk` service namespace
- **AND** the key is NOT written to SQLite or the filesystem

#### Scenario: Retrieve API key from keyring
- **WHEN** the application starts or a component requests an API key
- **THEN** the key is retrieved from the OS keyring if available

#### Scenario: Keyring unavailable fallback
- **WHEN** the OS keyring is not available (e.g., headless server)
- **THEN** the system logs a warning message
- **AND** falls back to environment variable lookup
- **AND** the user is notified that secure storage is unavailable

### Requirement: Legacy File Migration
The system SHALL provide one-time migration from legacy `API_KEY.txt` file storage to the secure keyring on first run.

#### Scenario: Migrate existing API keys
- **WHEN** the application starts
- **AND** an `API_KEY.txt` file exists with valid keys
- **AND** the keyring does not already contain stored keys
- **THEN** the system imports all keys from the file into the keyring
- **AND** displays a notification: "API keys migrated to secure storage"

#### Scenario: Skip migration if keyring has keys
- **WHEN** the application starts
- **AND** the keyring already contains API keys
- **THEN** the system skips migration
- **AND** ignores `API_KEY.txt` if present

### Requirement: Environment Variable Override
The system SHALL support environment variable overrides for API keys to enable CI/CD and containerized deployments.

#### Scenario: Environment variable takes precedence
- **WHEN** an environment variable (e.g., `OPENROUTER_API_KEY`) is set
- **THEN** the environment variable value is used instead of the keyring value

#### Scenario: No environment variable
- **WHEN** no environment variable is set for a given key
- **THEN** the system retrieves the key from the keyring

## MODIFIED Requirements

### Requirement: Functional Models and Theme Pages
The Models page SHALL allow editing the API key and selecting a default model, and those changes SHALL persist. The Theme page SHALL allow selecting theme mode, font family, window transparency, and keep-above behavior, and those changes SHALL persist and update the UI. **API keys entered on the Models page SHALL be stored securely in the OS keyring rather than in SQLite or configuration files.**

#### Scenario: Update model settings
- **WHEN** the user updates the API key or default model
- **THEN** the API key is stored in the OS keyring
- **AND** the default model selection persists to SQLite
- **AND** the new values are used for subsequent chats

#### Scenario: Update theme settings
- **WHEN** the user changes theme mode, font, transparency, or keep-above
- **THEN** the UI updates to reflect the new theme settings.

#### Scenario: API key field displays masked keyring value
- **WHEN** the user opens the Models settings page
- **AND** an API key is stored in the keyring
- **THEN** the API key field displays a masked representation (e.g., `sk-or-v1-••••••••bcα`)
