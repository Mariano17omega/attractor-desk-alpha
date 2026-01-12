## Context
Attractor Desk stores workspaces, sessions, and artifacts in a local SQLite database and renders a PySide6 UI backed by a LangGraph pipeline. The current RAG page is a placeholder and no indexing or retrieval exists. The requested change introduces local-first RAG using SQLite and optional OpenRouter embeddings without adding external vector databases.

## Goals / Non-Goals
- Goals:
  - Index PDFs imported as artifacts and optionally index text artifacts on save.
  - Provide hybrid retrieval (FTS5 + embeddings) with RRF fusion and reranking.
  - Keep retrieval scoped to session or workspace and enforce scope in SQL.
  - Keep UI responsive by running indexing off the main thread.
  - Provide configurable RAG settings with sensible defaults.
- Non-Goals:
  - External vector databases or hosted RAG services.
  - Automatic backfill of all existing artifacts in MVP.
  - Cross-device or multi-user indexing synchronization.

## Decisions
- Data model: add `rag_documents`, `rag_chunks`, `rag_document_sessions`, `rag_chunks_fts`, and `rag_embeddings` tables in the existing SQLite database.
- FTS synchronization: maintain `rag_chunks_fts` in the repository write path (single write path) instead of SQLite triggers.
- Chunking: split Markdown by headers with a character-based fallback and configurable size/overlap defaults.
- Embeddings: optional via OpenRouter embeddings; store float32 bytes and dims in SQLite. If no model configured, use a default embedding model (proposed: `openai/text-embedding-3-small`).
- Retrieval: hybrid lexical + vector retrieval with RRF fusion; heuristic rerank by default; optional LLM rerank when enabled.
- Graph integration: add a dedicated RAG subgraph that runs before response-generation nodes and writes `rag_*` state fields.
- Indexing triggers: PDF imports always index; text artifacts index on save only when the toggle is enabled.

## Risks / Trade-offs
- Vector scan cost in SQLite can be high; mitigate by scope-limited scans and caching per workspace when needed.
- LLM rerank adds latency and cost; keep disabled by default and user-configurable.
- FTS sync errors could desynchronize lexical results; mitigate by enforcing updates within repository writes.

## Migration Plan
- Extend schema in `Database.SCHEMA`; existing databases will create new tables automatically on startup.
- Indexing begins only for new PDF imports and toggled text artifact saves; no bulk backfill in MVP.
- Default settings keep RAG disabled until the user opts in.

## Open Questions
- None.
