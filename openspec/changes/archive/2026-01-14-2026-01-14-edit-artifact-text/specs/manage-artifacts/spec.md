# manage-artifacts

## ADDED Requirements

### Requirement: Manual Text Editing
The system SHALL allow the user to manually edit the content of text artifacts.

#### Scenario: Enter edit mode via double-click
- **GIVEN** a text artifact is displayed
- **WHEN** the user double-clicks on the text content
- **THEN** the artifact enters an edit mode
- **AND** the content is displayed as raw editable text
- **AND** a "Save" button becomes visible.

#### Scenario: Save edited content
- **GIVEN** a text artifact is in edit mode with modified content
- **WHEN** the user clicks the "Save" button
- **THEN** the modified content is saved to the artifact
- **AND** the artifact exits edit mode
- **AND** the content is re-rendered as Markdown.

#### Scenario: Cancel editing
- **GIVEN** a text artifact is in edit mode with modified content
- **WHEN** the user clicks "Cancel" (or functionality if added) or navigates away
- **THEN** the changes are discarded
- **AND** the artifact remains in its previous state (or exits edit mode without saving).
*(Note: User request only explicitly asked for Save, but Cancel is implied for standard UI behavior/safety. I will interpret "If the user does not click 'Save', no changes should be permanently applied" as needing a way to leave without saving, or just not saving until clicked).*

