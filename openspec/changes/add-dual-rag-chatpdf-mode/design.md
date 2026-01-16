## Context
- Current RAG graph has a single path with basic decide/select/rewrite/retrieve nodes and no notion of ChatPDF vs global scope.
- RAG storage only scopes by session/workspace; there is no shared global library or file monitoring, and retrieval cannot report which source answered.
- ChatPDF lacks a dedicated mode flag, viewer artifact, or cleanup for per-PDF RAG data; uploads are treated like generic PDF ingestions.
- Settings page has basic knobs (scope, chunking, k-values, toggles) but no global knowledge base controls, progress, or registry visibility.

## Goals / Non-Goals
- Goals: dual RAG nodes with mode-aware routing; shared global knowledge base with watcher-driven indexing; ChatPDF artifacts with viewer and session-scoped RAG; keep the existing artifact RAG node dedicated to canvas artifact retrieval; clear metadata/logging of RAG source; efficient/cached indexing with retries; UI controls for monitoring and status.
- Non-Goals: change reply prompting beyond appending rag_context; implement FAISS now (leave as future optional); add context highlighting inside the PDF viewer (not in this iteration).

## Decisions
- Conversation mode & routing: add `conversation_mode` (normal|chatpdf), `active_pdf_document_id`, and `rag_used`/`rag_route_debug` fields to state. `global_rag_node` runs when mode != chatpdf and retrieval is needed; `local_rag_node` runs when mode == chatpdf or a session PDF is active. Both attach `rag_context`, `rag_citations`, `rag_selected_chunk_ids`, and metadata about which node ran.
- Canvas artifact path: retain the current artifact-scoped RAG node for canvas flows (artifact generation/rewrites). It continues to retrieve session/workspace artifact content and is not replaced by the new global/local nodes; graph routing separates canvas artifact retrieval from chat-global/local retrieval.
- Scope semantics: introduce explicit `global` scope mapped to `workspace_id = "GLOBAL"`; retain `workspace`/`session` scopes for backwards compatibility. Local node always uses `session_id`; global node uses `GLOBAL` and may optionally merge workspace scope when configured.
- Storage strategy: reuse `rag_documents` with `workspace_id` set to `GLOBAL` for global library; add `indexed_at`, `file_size`, `source_path`, `stale_at` columns for lifecycle tracking. Seed a pseudo workspace row `GLOBAL` during migration to satisfy FK. Keep `rag_document_sessions` for ChatPDF attachments.
- Registry & watcher: add `rag_index_registry` keyed by `source_path`+`content_hash` to track status, retries, timestamps, and errors. `PdfWatcherService` wraps QFileSystemWatcher, debounces events (2–3s), hashes files, skips unchanged items, enqueues new/changed items, and retries up to 3 times with backoff.
- Indexing pipeline: batch PDF → Markdown conversions (5 at a time) with a thread pool; priority small-to-large; timeout ~5 minutes per PDF; cache converted markdown and embeddings keyed by content hash and model; dedupe identical chunks before embedding.
- ChatPDF artifact & viewer: new `ArtifactType.PDF_VIEWER` with metadata (`pdf_path`, `total_pages`, `current_page`, `rag_document_id`). Upload flow saves to session temp dir, creates artifact/tab, triggers local indexing, and shows an indexing status pill; viewer is read-only with zoom, prev/next, page jump, optional thumbnails.
- Cleanup: on session close, mark associated ChatPDF documents `stale_at`; background cleanup deletes stale docs/chunks/embeddings after a retention window (e.g., 7 days) and offers a manual "Clean old session PDFs" action in settings.
- Logging/metadata: nodes log which path ran and why; retrieval result carries `rag_used` (global/local), scope, counts, and candidate stats for debug display.

## Risks / Trade-offs
- Global workspace FK: inserting `GLOBAL` requires a seeded workspace row; alternatively loosening the FK reduces safety. Plan: seed a pseudo workspace during migration to preserve constraints.
- Watcher churn: rapid file writes could thrash the queue; debounce plus hashing aims to reduce load, but misconfigured large folders could still spike CPU. Mitigation: cap concurrent conversions and expose progress/errors in UI.
- Cache staleness: cached markdown/embeddings keyed by hash may hide updates if file changes without content hash change (unlikely). Documented assumption: hash changes when content changes.
- UX complexity: richer settings page and viewer controls add UI surface; keep defaults sensible (monitoring off by default, compact status panel).

## Migration Plan
1) Add schema migrations for new columns/table and seed a `GLOBAL` workspace row if absent; backfill `indexed_at` from `created_at` for existing docs.
2) Introduce registry population script to mark existing global-folder PDFs as `known` without reindexing; reindex on demand via button.
3) Roll out graph changes behind a feature flag if needed (`rag_mode_routing`), default on for new installs.
4) Default monitoring off; prompt user to pick a folder before enabling.
5) Validate by running openspec + targeted tests (repository, services, graph routing, watcher debounce) before enabling in UI.

## Resolved Questions
- Retention window for stale ChatPDF docs: 7 days.
- Default path for AttractorDeskRAG folder: `~/Documents/AttractorDeskRAG`.
- Global retrieval remains global-only (no workspace blending unless explicitly added later).
- Surface per-document embedding model/version in the document list for troubleshooting.
