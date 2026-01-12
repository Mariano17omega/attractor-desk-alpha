## 1. Data and persistence
- [x] 1.1 Extend SQLite schema with RAG tables, indexes, and FTS5 virtual table.
- [x] 1.2 Implement `rag_repository.py` with document/chunk CRUD, session attachments, and FTS sync on write.
- [x] 1.3 Add chunking utilities with header-aware splitting and overlap; add unit tests.

## 2. Embeddings and indexing
- [x] 2.1 Implement OpenRouter embeddings client with configurable model and sensible default.
- [x] 2.2 Implement `rag_service.py` indexing (content hash, chunking, embeddings, session links) in a worker thread.
- [x] 2.3 Wire PDF import and text artifact save (when toggled) to indexing.

## 3. Retrieval pipeline
- [x] 3.1 Implement FTS5 lexical retrieval with SQL scope enforcement.
- [x] 3.2 Implement vector retrieval (scope-limited), RRF fusion, and candidate selection.
- [x] 3.3 Implement heuristic rerank (default) and optional LLM rerank; add context builder and grounding checks.

## 4. RAG graph integration
- [x] 4.1 Add `rag_*` fields to `OpenCanvasState` and create the RAG subgraph.
- [x] 4.2 Integrate the subgraph into `open_canvas` routing and pass `session_id`/`workspace_id` in config.
- [x] 4.3 Append retrieved context to prompts and add grounding disclaimers when needed.

## 5. Settings and UI
- [x] 5.1 Replace the RAG placeholder page with settings controls for retrieval, chunking, and indexing.
- [x] 5.2 Persist RAG settings in `SettingsViewModel` and `SettingsRepository` with defaults.

## 6. Validation
- [x] 6.1 Add tests for chunking, repository FTS sync, retrieval fusion, and rerank heuristics.
- [x] 6.2 Add integration tests for indexing triggers and scope-restricted retrieval.
- [x] 6.3 Run `pytest` and any relevant linters/formatters.
