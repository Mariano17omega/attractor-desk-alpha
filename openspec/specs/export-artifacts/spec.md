# export-artifacts Specification

## Purpose
TBD - created by archiving change add-docling-pdf-artifacts. Update Purpose after archive.
## Requirements
### Requirement: Artifact export directory
The system SHALL export artifacts to `/home/m/Documents/Artifacts/Articles` and SHALL create the directory if it does not exist. The system SHALL update export files when the user switches sessions or closes the application.

#### Scenario: Export on session switch
- **WHEN** the user switches to another session
- **THEN** the artifacts from the previous session are exported or updated in `/home/m/Documents/Artifacts/Articles`.

#### Scenario: Export on app close
- **WHEN** the user closes the application
- **THEN** the artifacts from the active session are exported or updated in `/home/m/Documents/Artifacts/Articles`.

### Requirement: Export naming conventions
For PDF-ingested artifacts, the system SHALL name the export file using the PDF filename without extension. For chat-created artifacts, the system SHALL name the export file using `{session_title}-{tab_label}`. All artifact exports SHALL use a `.md` extension. If a PDF-based name already exists, the system SHALL append a numeric suffix to create a new file (e.g., `Doc.md`, `Doc-2.md`).

#### Scenario: Name exports for PDF and chat artifacts
- **WHEN** a PDF named `Report.pdf` is ingested
- **THEN** the export file is named `Report.md` (or `Report-2.md` if `Report.md` exists)
- **AND WHEN** a chat-created artifact tab is labeled `Art_1` in session `Chat_1`
- **THEN** the export file is named `Chat_1-Art_1.md`.

### Requirement: Export content formatting
Text artifact exports SHALL write the full Markdown content. Code artifact exports SHALL write a fenced code block using the artifact language when available.

#### Scenario: Export code artifact
- **WHEN** a code artifact is exported
- **THEN** the markdown file contains a fenced code block with the artifact language and code content.

