## ADDED Requirements
### Requirement: Screen Capture Actions
The system SHALL provide actions to capture the full screen of the cursor's monitor and to capture a user-selected screen region.

#### Scenario: Capture full screen
- **WHEN** the user triggers the full screen capture action
- **THEN** the system captures the active monitor into an image.

#### Scenario: Capture region
- **WHEN** the user triggers region capture and selects a region
- **THEN** the system captures only the selected region into an image.

### Requirement: Region Selection Overlay
The system SHALL display a full-screen overlay for region selection and SHALL allow cancelling the selection with the Escape key.

#### Scenario: Cancel selection
- **WHEN** the user presses Escape during region selection
- **THEN** the capture flow is cancelled without saving an image.

### Requirement: Capture Preview Confirmation
After a capture, the system SHALL display a preview dialog that allows confirming, cancelling, or retaking the capture before it is attached.

#### Scenario: Confirm capture
- **WHEN** the user confirms the preview
- **THEN** the capture proceeds to attachment handling.

#### Scenario: Retake capture
- **WHEN** the user chooses retake in the preview
- **THEN** the capture flow restarts.

### Requirement: Capture Storage and Attachment Handling
The system SHALL save confirmed captures to `/home/m/Documents/Attractor_Imagens`, creating the folder if it does not exist, and SHALL persist only file path references in the database. If the selected model is multimodal, the capture SHALL be attached to the next user prompt; otherwise, the system SHALL warn that the model is not compatible and SHALL not attach the capture.

#### Scenario: Attach capture for multimodal model
- **WHEN** the user confirms a capture and the selected model supports images
- **THEN** the capture file is saved, its path is stored, and the image is attached to the next prompt.

#### Scenario: Reject capture for non-multimodal model
- **WHEN** the user confirms a capture and the selected model does not support images
- **THEN** a warning is shown and the capture is not attached.
