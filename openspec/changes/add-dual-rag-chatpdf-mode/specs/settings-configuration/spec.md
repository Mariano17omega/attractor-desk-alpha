## ADDED Requirements
### Requirement: Global RAG configuration controls
The RAG settings page SHALL include a "Knowledge Base Folder" picker, an "Automatic Monitoring" toggle, an "Index All PDFs" button, and a "Check for New PDFs" button. Changes SHALL persist via the settings repository and drive watcher/registry behavior (monitoring disabled stops the watcher; path changes update the registry base path). The page SHALL display monitoring status (Active/Inactive) and the last update timestamp.

#### Scenario: Configure monitoring folder
- **WHEN** the user selects a new knowledge base folder and enables automatic monitoring
- **THEN** the selection and toggle persist
- **AND** the watcher monitors the new folder while the status shows Active and the last update timestamp is refreshed after the next scan.

### Requirement: RAG indexing status and document list
The RAG settings page SHALL show a status panel with total indexed documents, last update time, monitoring state, and the last five processed files. It SHALL render a table with columns [File name, Path, Indexed at, Status, Actions], filters by name/date/status, and support actions: re-index, remove from index, view details (chunks + embedding model). Bulk actions SHALL allow re-index/remove for selected rows. Bulk/manual operations SHALL display a progress bar with counters (e.g., "Processing PDF 45 of 120"), estimated time remaining, real-time error log, and a completion notification summarizing successes/errors.

#### Scenario: Bulk reindex with progress
- **WHEN** the user selects multiple documents and starts a bulk reindex
- **THEN** the table updates row statuses as work progresses, the progress bar and counters update in real time, errors appear in the log, and a completion notice summarizes successes and failures.
