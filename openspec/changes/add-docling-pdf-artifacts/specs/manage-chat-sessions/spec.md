## MODIFIED Requirements
### Requirement: Persisted Sessions and Artifacts
The system SHALL persist workspaces, sessions, messages, and artifacts locally and restore them on startup. The system SHALL associate chat messages and artifacts with the active session so selecting a session restores its history and the full artifact collection, including the active artifact and its version history.

#### Scenario: Restart persistence
- **WHEN** the application restarts
- **THEN** previously saved workspaces, sessions, messages, and artifacts are restored.

#### Scenario: Session artifact restoration
- **WHEN** a user selects a session with saved artifacts
- **THEN** the artifacts panel displays the artifact tabs for that session
- **AND** the active artifact is shown with its latest content.
