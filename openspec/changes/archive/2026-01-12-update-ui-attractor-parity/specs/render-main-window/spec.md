## ADDED Requirements
### Requirement: Main Window Layout Parity
The system SHALL render the main window with a left-to-right horizontal splitter containing a chat panel, a sessions/history sidebar, and an artifacts panel that match the reference layout hierarchy. The artifacts panel SHALL be the rightmost section and SHALL be shown or hidden via the chat header memory button without overlapping the chat or sessions panels. The main window title SHALL be set to `Attractor Desk`.

#### Scenario: Launch layout
- **WHEN** the application launches
- **THEN** the main window title reads `Attractor Desk`
- **AND** the chat panel and sessions/history sidebar are visible
- **AND** the artifacts panel is hidden in the rightmost splitter section.

#### Scenario: Toggle artifacts panel
- **WHEN** the user activates the memory button in the chat header
- **THEN** the artifacts panel becomes visible on the right without hiding the chat or sessions panels.

### Requirement: Chat Panel Structure
The system SHALL render the chat panel header, message list, and input area to mirror the reference structure, including branding labels, an agent selector placeholder, a memory button, a sidebar toggle, a history loader, an attachment control placeholder, and send/cancel controls. The chat header branding labels SHALL read `AMADEUS CHANNEL` and `SECURE CONNECTION // AMADEUS PROTOCOL V1.02`.

#### Scenario: Header composition
- **WHEN** the chat panel renders
- **THEN** the header includes branding labels, an agent selector control, a memory button, and a sidebar toggle arranged as in the reference
- **AND** the branding labels read `AMADEUS CHANNEL` and `SECURE CONNECTION // AMADEUS PROTOCOL V1.02`.

#### Scenario: Input area composition
- **WHEN** the input area renders
- **THEN** it includes an add-attachment control, a message input, and send/cancel controls arranged as in the reference.
