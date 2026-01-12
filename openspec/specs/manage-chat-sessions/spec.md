# manage-chat-sessions Specification

## Purpose
TBD - created by archiving change update-ui-attractor-parity. Update Purpose after archive.
## Requirements
### Requirement: Sessions Sidebar Layout
The system SHALL provide a sessions/history sidebar that mirrors the reference layout, including a workspace selector row, a sessions list with create/delete actions, and bottom action buttons for knowledge base, deep research, and settings. See render-main-window for the sidebar placement in the main layout.

#### Scenario: Sidebar layout
- **WHEN** the main window renders
- **THEN** the sessions/history sidebar shows a workspace selector row, a sessions list with add/delete controls, and bottom action buttons aligned to the reference.

### Requirement: Workspace Management
The system SHALL allow users to create, select, and delete workspaces from the workspace selector, and SHALL scope the sessions list to the selected workspace.

#### Scenario: Create workspace
- **WHEN** a user creates a new workspace
- **THEN** the workspace appears in the selector and becomes available for selection.

#### Scenario: Select workspace
- **WHEN** a user selects a workspace
- **THEN** the sessions list updates to show sessions belonging to that workspace.

#### Scenario: Delete workspace
- **WHEN** a user deletes a workspace
- **THEN** the workspace and its sessions are removed from the selector and list.

### Requirement: Session Management
The system SHALL allow users to create, select, and delete chat sessions from the sessions list and SHALL update the chat view to the selected session.

#### Scenario: Create session
- **WHEN** a user creates a new session
- **THEN** the session appears in the sessions list and becomes the active session.

#### Scenario: Select session
- **WHEN** a user selects a session from the list
- **THEN** the chat view updates to display that session's message history.

#### Scenario: Delete session
- **WHEN** a user deletes a session
- **THEN** the session is removed from the list and its data is no longer accessible.

### Requirement: Persisted Sessions and Artifacts
The system SHALL persist workspaces, sessions, messages, and artifacts locally and restore them on startup. The system SHALL associate chat messages and artifacts with the active session so selecting a session restores its history and the full artifact collection, including the active artifact and its version history.

#### Scenario: Restart persistence
- **WHEN** the application restarts
- **THEN** previously saved workspaces, sessions, messages, and artifacts are restored.

#### Scenario: Session artifact restoration
- **WHEN** a user selects a session with saved artifacts
- **THEN** the artifacts panel displays the artifact tabs for that session
- **AND** the active artifact is shown with its latest content.

### Requirement: Automatic Session Title Generation
The system SHALL generate a concise session title after the first user-assistant exchange and persist the title to the session record.

#### Scenario: Title generated after first exchange
- **WHEN** the first assistant response completes
- **THEN** the system SHALL generate a 2-5 word title based on the conversation and any artifact context and update the session entry.

