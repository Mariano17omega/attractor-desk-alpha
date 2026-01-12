# rag-indexing Specification

## Purpose
TBD - created by archiving change add-local-rag. Update Purpose after archive.
## Requirements
### Requirement: RAG Storage in SQLite
The system SHALL store RAG documents, chunks, session attachments, and embeddings in the existing SQLite database and SHALL use SQLite FTS5 for lexical indexing of chunk content. The system MUST NOT require an external vector database in the MVP. Related capabilities: rag-retrieval.

#### Scenario: Initialize RAG tables
- **WHEN** the application initializes the database
- **THEN** the RAG tables and FTS index are available for indexing and retrieval.

### Requirement: Artifact Indexing Triggers
The system SHALL index PDFs imported as artifacts automatically. The system SHALL index text artifacts on save only when the `rag.index_text_artifacts` setting is enabled. The system SHALL compute a content hash and skip reindexing when unchanged. The system SHALL attach indexed documents to the current session when one is available. Indexing MUST run off the UI thread.

#### Scenario: Index PDF import
- **WHEN** a user imports a PDF into a session
- **THEN** the artifact content is indexed and linked to the session.

#### Scenario: Index text artifact when enabled
- **WHEN** a user saves a text artifact and `rag.index_text_artifacts` is enabled
- **THEN** the artifact content is indexed; if the hash is unchanged, indexing is skipped.

### Requirement: Chunking and FTS Synchronization
The system SHALL split Markdown by headers with a character-based fallback and configurable chunk size and overlap. Each chunk SHALL store its section title when available and token count when provided by a tokenizer. The system SHALL update `rag_chunks_fts` within the same repository write path whenever chunks are inserted or deleted.

#### Scenario: Indexing writes chunks and FTS rows
- **WHEN** a document is indexed
- **THEN** chunks are stored with section titles and the FTS index reflects the same chunk set.

### Requirement: Embeddings Persistence
When embeddings are enabled and an API key is configured, the system SHALL generate embeddings for each chunk using the configured model or a default model and store float32 bytes with explicit dimensions. When embeddings are disabled or keys are missing, the system SHALL skip embedding generation.

#### Scenario: Embeddings enabled
- **WHEN** embeddings are enabled and a document is indexed
- **THEN** embeddings are generated and stored alongside chunk records.

