# Change: Add Local RAG for Artifacts

## Why
Users need answers grounded in their local PDFs and text artifacts without adding external services or a vector database. A local-first RAG implementation aligns with the existing SQLite stack and keeps the UI responsive while improving answer quality.

## What Changes
- Add SQLite-backed RAG storage, indexing, chunking, and optional embeddings for artifacts.
- Introduce a RAG subgraph integrated into the Open Canvas graph to enrich prompts with retrieved context.
- Replace the RAG settings placeholder with functional controls, including toggles for indexing and reranking.

## Impact
- Affected specs: settings-configuration (modify), rag-indexing (new), rag-retrieval (new)
- Affected code: core/persistence/database.py, core/persistence/rag_repository.py, core/services/rag_service.py, core/utils/chunking.py, core/llm/embeddings.py, core/graphs/rag/*, core/graphs/open_canvas/state.py, core/graphs/open_canvas/graph.py, core/graphs/open_canvas/nodes/* prompts, ui/widgets/configuration/rag_page.py, ui/viewmodels/settings_viewmodel.py, ui/viewmodels/chat_viewmodel.py
