## 1. Implementation
- [x] 1.1 Add DB migration/seeding for `GLOBAL` workspace, `rag_documents` metadata columns (`indexed_at`, `file_size`, `source_path`, `stale_at`) and `rag_index_registry`; update RagRepository queries for `global|workspace|session` scopes.
- [x] 1.2 Build registry APIs and GlobalRagService for manual/bulk indexing and stats; add hashing/dedupe + shared embedding cache keyed by content hash/model.
- [x] 1.3 Implement PdfWatcherService (QFileSystemWatcher + debounce/queue/retry) and wiring to trigger global indexing when monitoring is enabled.
- [x] 1.4 Introduce LocalRagService hooks for ChatPDF uploads: session temp save, local indexing, status callbacks, and stale marking/cleanup after retention window.
- [x] 1.5 Extend LangGraph: add `conversation_mode` state, `global_rag_node`/`local_rag_node` with conditional edges, metadata (`rag_used`, debug), and ensure nodes run before response generation.
- [x] 1.6 Expand RAG settings UI/viewmodel: folder picker, monitoring toggle, manual scan/index buttons, status/progress panel, document table with filters/actions, persistence of new keys.
- [x] 1.7 Add PDF viewer artifact type/tab and widget (zoom/nav/page jump, status pill, optional thumbnails); ensure upload flow auto-creates the viewer artifact, switches mode, and shows indexing state.
- [x] 1.8 Implement cleanup tools: scheduled deletion of stale ChatPDF docs after N days and a manual "Clean old session PDFs" action.
- [x] 1.9 Performance tuning: batch PDF conversions (5 at a time), priority queue small-to-large, per-document timeout, chunk deduplication, and reuse cached markdown/embeddings.

## 2. Validation
- [x] 2.1 Unit tests: RagRepository scope queries (global/workspace/session), registry hashing/retries, watcher debounce, and graph routing for both modes.
- [ ] 2.2 Integration tests: end-to-end indexing/retrieval for global vs ChatPDF, metadata (`rag_used`, citations) propagation, and UI viewmodels for settings + PDF viewer state transitions.
- [ ] 2.3 Manual QA: monitor folder adds/removes while app runs, bulk index progress bar for 50+ PDFs, ChatPDF mode toggle normal→chatpdf→normal, retention cleanup run.
- [x] 2.4 Run `openspec validate add-dual-rag-chatpdf-mode --strict` and address any issues before implementation.
