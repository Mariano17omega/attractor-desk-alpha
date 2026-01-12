## ADDED Requirements
### Requirement: Automatic Session Title Generation
The system SHALL generate a concise session title after the first user-assistant exchange and persist the title to the session record.

#### Scenario: Title generated after first exchange
- **WHEN** the first assistant response completes
- **THEN** the system SHALL generate a 2-5 word title based on the conversation and any artifact context and update the session entry.
