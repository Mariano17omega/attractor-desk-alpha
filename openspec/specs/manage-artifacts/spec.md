# manage-artifacts Specification

## Purpose
TBD - created by archiving change add-docling-pdf-artifacts. Update Purpose after archive.
## Requirements
### Requirement: Multi-artifact collections
The system SHALL maintain an ordered collection of artifacts per session, each with its own version history. One artifact SHALL be marked as active, and artifact updates requested by the user SHALL apply only to the active artifact.

#### Scenario: Active artifact scoping
- **WHEN** multiple artifacts exist and the user selects `Art_2`
- **THEN** subsequent chat-driven updates modify only `Art_2`
- **AND** other artifacts remain unchanged.

### Requirement: Artifact tab rendering and naming
The artifacts panel SHALL render one tab per artifact plus two creation tabs labeled `New_Art` and `New_Code`. Text artifacts SHALL use tab labels `Art_N` and code artifacts SHALL use `Code_N`, where `N` is the next sequential number for that type based on creation order.

#### Scenario: Tab naming for mixed artifacts
- **WHEN** the user creates a text artifact, a code artifact, then another text artifact
- **THEN** the tabs are labeled `Art_1`, `Code_1`, and `Art_2` in creation order
- **AND** the `New_Art` and `New_Code` tabs remain available.

### Requirement: Blank artifact creation
Selecting `New_Art` or `New_Code` SHALL create a new blank artifact, set it as active, and add a corresponding tab. Blank artifacts SHALL use the tab label as the default title and start with empty content (code artifacts SHALL default to language `other`).

#### Scenario: Create blank text artifact
- **WHEN** the user selects `New_Art`
- **THEN** a new text artifact with empty Markdown content is created
- **AND** it becomes the active artifact.

