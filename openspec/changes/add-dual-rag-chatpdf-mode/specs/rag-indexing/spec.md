## MODIFIED Requirements
### Requirement: RAG Storage in SQLite
The system SHALL store RAG documents, chunks, session attachments, and embeddings in the existing SQLite database and SHALL use SQLite FTS5 for lexical indexing of chunk content. The system SHALL support a reserved `workspace_id = "GLOBAL"` for shared documents alongside normal workspace/session scopes and SHALL track per-document metadata (`indexed_at`, `file_size`, `content_hash`, `source_path`, `stale_at`) to manage lifecycle and deduplication. The schema SHALL add a registry table for watched files and seed a `GLOBAL` workspace entry (or equivalent FK-safe approach) so inserts succeed without weakening constraints. The system MUST NOT require an external vector database in the MVP. Related capabilities: rag-retrieval.

#### Scenario: Initialize RAG tables
- **WHEN** the application initializes or migrates the database
- **THEN** the RAG tables, FTS index, registry table, and `GLOBAL` workspace entry exist with the new metadata columns available for storage and retrieval.

## ADDED Requirements
### Requirement: Global knowledge base indexing
The system SHALL index PDFs from a user-selected global folder into `rag_documents` with `workspace_id = "GLOBAL"`, storing `source_path`, `source_name`, `content_hash`, `indexed_at`, and `file_size`. Hash-matching SHALL prevent duplicate reindexing, and manual/bulk runs SHALL refresh `indexed_at` when content is unchanged. Global retrieval SHALL search only documents with `workspace_id = "GLOBAL"` and SHALL not attach global documents to sessions.

#### Scenario: Index global PDF
- **WHEN** the user triggers a manual index of the global folder
- **THEN** new PDFs are hashed and inserted under `workspace_id = "GLOBAL"`
- **AND** unchanged files are skipped with `indexed_at` refreshed
- **AND** subsequent global retrieval only considers those global documents.

### Requirement: RAG file monitoring and registry
When "Automatic Monitoring" is enabled, the system SHALL watch the configured global folder via QFileSystemWatcher (or equivalent), debounce events (2–3 seconds), hash changed files, and enqueue new or modified PDFs into an async processing queue. The system SHALL maintain a registry row per `source_path` + `content_hash` with status, retry count (up to 3 attempts), last_seen/indexed timestamps, and error message. Registry lookups SHALL skip already-indexed hashes and mark failures for retry.

#### Scenario: Detect new PDF while running
- **WHEN** a new PDF is saved into the watched folder
- **THEN** the watcher debounces the event, records the hash in the registry, enqueues the file once, and processes it unless the hash already exists.

### Requirement: Session-bound ChatPDF indexing lifecycle
ChatPDF uploads SHALL index into `rag_documents` scoped to the current `session_id` (and current workspace for FK integrity) and record `source_path`, `content_hash`, and `rag_document_id` on the associated PDF viewer artifact. On session close, the system SHALL mark attached ChatPDF documents `stale_at`, and a cleanup job SHALL delete stale ChatPDF documents, chunks, embeddings, and registry rows after a configurable retention window. A manual "Clean old session PDFs" action SHALL force immediate cleanup of stale ChatPDF entries.

#### Scenario: ChatPDF lifecycle
- **WHEN** a user uploads a PDF in ChatPDF mode
- **THEN** the PDF is indexed under the session scope with stored metadata
- **AND** when the session closes it is marked stale
- **AND** stale ChatPDF documents are removed after the retention window or when the user runs the cleanup action.

### Requirement: Indexing performance and caching
The indexing pipeline SHALL support batching multiple PDFs (e.g., 5 concurrently) using a thread pool, prioritize smaller PDFs first, and enforce a per-document timeout (e.g., 5 minutes). The system SHALL cache PDF→Markdown conversions and embeddings keyed by content hash and embedding model, and SHALL deduplicate identical chunks before embedding to reduce work.

#### Scenario: Batch index large folder
- **WHEN** the user indexes a folder containing many PDFs of varying sizes
- **THEN** the system processes up to the configured batch size in parallel, favors smaller files first, aborts files that exceed the timeout, and reuses cached conversions/embeddings for unchanged content.
