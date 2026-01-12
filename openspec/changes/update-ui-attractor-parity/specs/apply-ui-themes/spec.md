## ADDED Requirements
### Requirement: Reference Theme Definitions
The system SHALL use theme definitions copied from Documentation/attractor_desk_Reference/views/styles.py, including color tokens and QSS rules, as the source of truth for UI styling.

#### Scenario: Apply reference stylesheet
- **WHEN** the application initializes
- **THEN** the active stylesheet matches the copied reference theme definitions.

### Requirement: Theme Selection and Persistence
The system SHALL apply light or dark themes based on the selected theme mode and SHALL persist the selection across restarts.

#### Scenario: Switch theme
- **WHEN** a user changes the theme mode in settings
- **THEN** the application updates its styling to the selected theme.

#### Scenario: Restore theme
- **WHEN** the application restarts
- **THEN** the previously selected theme mode is restored.

### Requirement: UI Assets Parity
The system SHALL bundle UI assets copied from Documentation/attractor_desk_Reference/assets and use them for icons, branding, and profile avatars in the UI.

#### Scenario: Load assets
- **WHEN** the main window renders
- **THEN** UI icons and avatars load from the copied assets.
