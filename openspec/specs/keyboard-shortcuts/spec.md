# keyboard-shortcuts Specification

## Purpose
TBD - created by archiving change add-shortcuts-screen-capture. Update Purpose after archive.
## Requirements
### Requirement: Application Shortcut Registration
The system SHALL register in-app keyboard shortcuts from the persisted shortcut bindings and map them to application actions, including send message, new session, new workspace, cancel generation, open settings, capture full screen, and capture region. Shortcut bindings with empty key sequences SHALL be disabled.

#### Scenario: Apply updated shortcuts
- **WHEN** the user saves updated shortcut bindings
- **THEN** the application updates the active shortcuts to match the new bindings.

#### Scenario: Disable a shortcut
- **WHEN** a shortcut binding is cleared
- **THEN** the associated action no longer triggers from the keyboard.

### Requirement: Send Message Shortcut
The message input SHALL use the configured send message shortcut when present and SHALL fall back to the default send shortcut when no binding is configured.

#### Scenario: Send message via shortcut
- **WHEN** the user presses the configured send shortcut in the message input
- **THEN** the message is sent without requiring a mouse click.

