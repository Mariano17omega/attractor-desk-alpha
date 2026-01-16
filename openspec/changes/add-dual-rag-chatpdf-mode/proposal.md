# Change: Dual RAG routing for Global + ChatPDF

## Why
- Retrieval is currently scoped per session/workspace only; users cannot keep a shared PDF knowledge base separate from ChatPDF uploads.
- ChatPDF flow lacks a dedicated mode indicator, viewer artifact, and per-PDF RAG lifecycle, making it hard to reason about routing or cleanup.
- No automated indexing pipeline exists for a global folder of PDFs, so users must re-index manually and risk duplicate/slow runs.

## What Changes
- Add mode-aware LangGraph RAG nodes (`global_rag_node`, `local_rag_node`) with routing driven by conversation state and per-response metadata/debug logs.
- Introduce a global RAG store (workspace_id = "GLOBAL") with hashing, registry, and file-watcher–driven indexing plus shared embeddings cache.
- Deliver ChatPDF artifacts with a PDF viewer widget, session-scoped indexing, and lifecycle cleanup for stale session PDFs.
- Expand RAG settings with global folder selection, automatic monitoring toggle, manual scan/index actions, progress/status panels, and document list management.
- Optimize indexing throughput (batching/priority/timeout, cached conversions) and track which RAG source powered each reply.

## Impact
- Affected specs: rag-indexing, rag-retrieval, settings-configuration, chatpdf-mode (new capability).
- Affected code: core/graphs/open_canvas/graph.py, core/graphs/rag/graph.py + nodes, core/services/rag_service.py and new global/local services, core/persistence/rag_repository.py + database schema/migrations, ui/viewmodels (chat/settings), ui/widgets (config RAG page, PDF viewer, status panels), watcher service.

## Architecture diagram
```
[User Message]
    |
    v
[OpenCanvas Router] --> [RAG Router]
    |                     |
    | mode=chatpdf        | mode=normal
    v                     v
[local_rag_node]      [global_rag_node]
    |                     |
    |--(context+metadata)->|
           v
      [Response Node]
```
Supporting services:
- Global watcher/registry -> Global RAG store (workspace_id="GLOBAL")
- ChatPDF upload -> session temp file -> local index (session_id) -> PDF viewer artifact/tab
```
[AttractorDeskRAG folder] --watch/scan--> [Registry + Hashing] --queue--> [Global Indexer]
```

## Decision flowchart (global vs local RAG)
```
Start message
  |
  |-- Is rag_enabled? ---- no --> Skip RAG, generator uses empty context
  |
  yes
  |
  |-- conversation_mode == "chatpdf" OR has_session_pdf? -- yes --> run local_rag_node (session_id)
  |                                                           |
  |                                                           --> set rag_used="local"; attach metadata/debug
  |-- otherwise ----------------------------------------------> run global_rag_node (workspace_id="GLOBAL")
                                                              --> set rag_used="global"; attach metadata/debug
  |
  v
Response generation node (prepends rag_context when present)
```

## Database schema (proposed additions)
- `rag_documents`: support `workspace_id = "GLOBAL"` records; add `indexed_at`, `file_size`, `content_hash` (already present), `source_path`, `stale_at` to manage cleanup; keep FK strategy by seeding a "GLOBAL" workspace row or gating FK checks during migration.
- `rag_document_sessions`: continue for session attachments; ChatPDF uploads attach to session_id and mark stale on session close.
- `rag_chunks`, `rag_chunks_fts`, `rag_embeddings`: unchanged structure but queries accept a `scope` of `global|workspace|session`.
- New registry table (e.g., `rag_index_registry`): `source_path`, `content_hash`, `status`, `retry_count`, `last_seen_at`, `last_indexed_at`, `error_message` to drive watcher + manual scans.

## Internal API outline
- `GlobalRagService`: index PDFs from folder (manual/bulk/scan), dedupe by hash, batch convert/embed, expose stats (indexed count, last update, failures).
- `LocalRagService`: index a single ChatPDF upload, track session document_id, mark stale, and enqueue cleanup after retention window.
- `PdfWatcherService`: Qt QFileSystemWatcher wrapper with debounce + async queue, emits `new_pdfs_detected(List[str])`, runs hashing/registry lookups, retries up to 3x.
- Graph nodes: `global_rag_node` and `local_rag_node` accept `conversation_mode`, `session_id`, `workspace_id`, return `rag_context`, `rag_citations`, `rag_used`, and debug info describing activation path and scope.

## Wireframes (text)
- RAG settings page (Global section): folder picker row, toggle for "Automatic monitoring", buttons for "Index all PDFs" and "Check for new PDFs", status chips (Active/Inactive, Last update), progress bar + "Processing PDF X of Y" when running, table listing [Name | Path | Indexed at | Status | Actions].
- PDF viewer artifact tab: header with filename + status pill (Indexing/Ready/Error), toolbar (Zoom -, Zoom +, page input, prev/next), optional thumbnail sidebar toggle; footer shows "Page N of M" and indexing state.

## User stories
- As a researcher, I want to drop new papers into my AttractorDeskRAG folder and have them auto-indexed so I can ask questions in any session without manual uploads.
- As a user chatting with a specific PDF, I want the app to stay in ChatPDF mode and only use that document’s context, with a clear indicator of which RAG source answered.
- As a maintainer, I want failed PDFs to retry a few times and surface errors in the settings status panel so I can fix bad files quickly.

## Detailed use cases
- Academic: auto-index a thesis library globally, then ChatPDF a single PDF chapter with local-only answers.
- Developer: keep API reference PDFs in the global base while running ChatPDF on a release notes PDF to draft upgrade guides.
- Compliance: monitor a folder of policy PDFs globally while opening a specific contract in ChatPDF to verify clauses with local-only retrieval.
