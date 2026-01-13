## ADDED Requirements
### Requirement: PDF ingestion via attachment control
The system SHALL let the user select a PDF from the chat input "+" control and SHALL immediately convert the PDF to Markdown using Docling. The system SHALL create a new text artifact with the converted Markdown content and set it as the active artifact. The artifact title SHALL be derived from the PDF file name without the extension.

#### Scenario: Ingest PDF into new artifact
- **WHEN** the user clicks the "+" control and selects a PDF file
- **THEN** the PDF is converted to Markdown via Docling
- **AND** a new text artifact is created with the converted Markdown
- **AND** the new artifact becomes the active artifact.

### Requirement: PDF ingestion always creates a new artifact
Each PDF selection SHALL create a new artifact entry even if another artifact is currently active.

#### Scenario: Multiple PDF ingestions
- **WHEN** the user ingests two PDFs in the same session
- **THEN** two distinct text artifacts appear in the artifact tabs
- **AND** the most recently ingested artifact is active.
