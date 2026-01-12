## ADDED Requirements
### Requirement: Shortcuts Configuration Page
The system SHALL provide a Shortcuts configuration page that lists available shortcut actions with their key sequences and descriptions, allows editing key sequences, and offers a reset to defaults option. Changes SHALL update the in-memory settings immediately and SHALL persist only when the user saves the configuration dialog.

#### Scenario: Edit shortcut binding
- **WHEN** the user edits a shortcut key sequence on the Shortcuts page
- **THEN** the new key sequence is shown in the list and becomes the pending setting value.

#### Scenario: Reset shortcuts
- **WHEN** the user resets shortcuts to defaults
- **THEN** the list shows the default key sequences for all actions.

## MODIFIED Requirements
### Requirement: Placeholder Pages
The Deep Research, RAG, and Memory pages SHALL be accessible from the sidebar and SHALL display placeholder layouts consistent with the reference without altering application behavior.

#### Scenario: Placeholder navigation
- **WHEN** the user navigates to a placeholder page
- **THEN** the page renders placeholder content and does not modify settings or runtime behavior.
