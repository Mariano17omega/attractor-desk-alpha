# RAG Architecture for Attractor Desk (Implementation Guide)

## Purpose and scope
This document describes how to implement Retrieval-Augmented Generation (RAG) in the current Attractor Desk Python desktop app. It focuses on local PDFs imported as artifacts and text artifacts stored in sessions. It avoids adding external services or vector databases so it fits the existing stack (MVP: SQLite-only).

## Current codebase constraints
- Language: Python 3.11+, PySide6 UI, LangGraph core (`core/graphs/open_canvas`).
- Persistence: SQLite via `core/persistence/database.py` (default `~/.open_canvas/database.db`).
- Artifacts: stored in the `artifacts` table via `core/persistence/artifact_repository.py` (stored as BLOB payloads).
- PDF ingestion: `core/services/docling_service.py` converts PDF to Markdown and `ui/viewmodels/chat_viewmodel.py` creates a text artifact.
- No RAG indexes or vector store dependencies are present today.

## Design decisions (aligned with current infrastructure)
- Use SQLite for document and chunk storage to stay consistent with existing persistence.
- Use SQLite FTS5 for lexical retrieval; it is built into SQLite and avoids new dependencies.
- Store embeddings in SQLite as BLOB (float32 bytes) and compute vector similarity in-process (no external vector DB).
- Use Hybrid RAG: lexical retrieval + vector retrieval in parallel, fused with RRF.
- Use reranking after fusion (hybrid heuristic by default; optional LLM rerank via OpenRouter for high-stakes queries).
- Add an agentic RAG subgraph for decisions (retrieve or not, scope, query rewrite, grounding check).
- Keep RAG logic in the core layer so UI remains thin and the LangGraph graph can call it.

## Component placement
| Component | Location | Responsibility |
| --- | --- | --- |
| RAG orchestrator | `core/services/rag_service.py` | Index artifacts, run retrieval, build context for prompts |
| SQLite access | `core/persistence/rag_repository.py` | CRUD for RAG tables and FTS index |
| Chunking helpers | `core/utils/chunking.py` | Split Markdown into chunks with overlap |
| Embeddings client | `core/llm/embeddings.py` | OpenRouter embeddings via httpx |
| RAG subgraph | `core/graphs/rag/*` | Agentic decisions, retrieval, fusion, rerank, context build |
| Graph integration | `core/graphs/open_canvas/graph.py` | Attach RAG subgraph before prompt nodes |
| Settings UI | `ui/widgets/configuration/rag_page.py` | RAG configuration inputs |
| Settings model | `ui/viewmodels/settings_viewmodel.py` | Persist RAG settings via `SettingsRepository` |

## SQLite schema additions
Extend the schema in `core/persistence/database.py` with RAG tables. These tables live in the same SQLite file as sessions and artifacts.

```sql
-- Documents indexed for RAG (workspace-first)
CREATE TABLE IF NOT EXISTS rag_documents (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    artifact_entry_id TEXT,
    source_type TEXT NOT NULL, -- "pdf" | "artifact"
    source_name TEXT NOT NULL,
    source_path TEXT,
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_rag_documents_workspace_id ON rag_documents(workspace_id);

-- Optional link: which sessions "attach" which documents
CREATE TABLE IF NOT EXISTS rag_document_sessions (
    document_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (document_id, session_id),
    FOREIGN KEY (document_id) REFERENCES rag_documents(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_rag_doc_sessions_session_id ON rag_document_sessions(session_id);

-- Chunked text
CREATE TABLE IF NOT EXISTS rag_chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    section_title TEXT,
    content TEXT NOT NULL,
    token_count INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY (document_id) REFERENCES rag_documents(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_document_id ON rag_chunks(document_id);

-- FTS5 index for lexical retrieval
CREATE VIRTUAL TABLE IF NOT EXISTS rag_chunks_fts USING fts5(
    chunk_id UNINDEXED,
    content,
    section_title,
    source_name
);

-- Embeddings (float32 bytes)
CREATE TABLE IF NOT EXISTS rag_embeddings (
  chunk_id TEXT PRIMARY KEY,
  model TEXT NOT NULL,
  dims INTEGER NOT NULL,
  embedding_blob BLOB NOT NULL, -- float32 bytes
  created_at TEXT NOT NULL,
  FOREIGN KEY (chunk_id) REFERENCES rag_chunks(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_rag_embeddings_model ON rag_embeddings(model);
````

Notes:

* `artifact_entry_id` is not a foreign key because artifact entries are stored inside the artifact payload (not as normalized rows).
* Keep `rag_chunks_fts` synchronized when chunks are inserted or deleted.
* All FTS queries must apply scope at SQL time using JOINs with `rag_chunks` → `rag_documents` (and `rag_document_sessions` when `scope=session`). Do not filter results in Python after ranking, because that skews the ranking and may return out-of-scope chunks.
* Consider adding triggers to keep FTS synchronized, or enforce synchronization at the repository layer (single write path).

## Ingestion and indexing flow

Primary trigger is the existing PDF import path.

1. User imports a PDF (`ui/widgets/chat_panel.py` -> `ChatViewModel.import_pdf`).
2. `DoclingService` converts PDF to Markdown.
3. `ChatViewModel` creates a text artifact and saves it via `ArtifactRepository`.
4. `RagService.index_artifact(...)` is called with:

   * `workspace_id` and `session_id` from `SessionRepository`
   * `artifact_entry_id` from the newly created `ArtifactEntry`
   * `source_name` from `ArtifactExportMeta.source_pdf`
   * Markdown content from the artifact
5. `RagService`:

   * Computes a `content_hash` and skips reindex if unchanged.
   * Chunks Markdown via `core/utils/chunking.py`.
   * Upserts `rag_documents` and writes `rag_chunks`.
   * Updates `rag_chunks_fts`.
   * Optionally creates embeddings and stores them in `rag_embeddings` (BLOB).

Session attachment behavior:

* If the artifact is imported during a chat session, `RagService` should create/keep a link:

  * `INSERT OR IGNORE INTO rag_document_sessions(document_id, session_id, created_at) ...`
* This allows `scope=session` retrieval without duplicating documents or chunks.

Optional trigger:

* Text artifacts created by the user can be indexed on save if an "Index text artifacts" setting is enabled.

Threading:

* Indexing should run in a worker thread (similar to `DoclingService`) to avoid blocking the UI.

## Chunking strategy

Implement a small, dependency-free chunker:

* Split by Markdown headers when present.
* Fallback to character-based splitting with overlap.
* Defaults: `chunk_size_chars = 1200`, `chunk_overlap_chars = 150`.
* Store `section_title` when a header is the anchor for a chunk.
* Store `token_count` if a tokenizer is available (optional in MVP, but recommended for future context budgeting).

## Embeddings and vectorization

Embeddings are optional and should be enabled only when an OpenRouter API key is configured.

* Implement `core/llm/embeddings.py` using the OpenRouter embeddings endpoint.
* Use the same API key already stored in settings (`SettingsViewModel.api_key`), with `core/config.get_openrouter_api_key()` as fallback.
* Store embeddings as BLOB float32 bytes in `rag_embeddings.embedding_blob` with explicit `dims`.
* Vector retrieval loads embeddings for the requested scope and scores with cosine similarity in-process.
* If embeddings are disabled or missing, retrieval falls back to FTS5-only (lexical retrieval).

Performance note (MVP):

* For `scope=session`, vector retrieval should only scan embeddings attached to that session (via `rag_document_sessions`) to keep N small.
* For `scope=workspace`, consider caching embeddings in memory (LRU keyed by workspace_id + model) to avoid repeated blob decoding.

## Retrieval flow (Hybrid + Reranking + Agentic)

1. Decide whether to retrieve:

   * Agentic node inspects the user message and current artifact state.
   * If the request is general chat, skip retrieval and keep `rag_context` empty.

2. Select scope:

   * Default to current session.
   * Allow workspace scope for cross-session queries.
   * Scope must be enforced at SQL time for FTS and by scope-limited embedding scans (not post-filtering in Python).

3. Query rewrite (optional):

   * Generate 1 to 3 rewrite queries for better recall.

4. Hybrid retrieval (per query):

   * Lexical (FTS5): query `rag_chunks_fts` joined with `rag_chunks` and `rag_documents` to enforce scope in SQL. Keep top `K_lex` per query.
   * Vector: embed the query (if embeddings enabled) and score chunk embeddings in the same scope. Keep top `K_vec` per query.

   Example: lexical retrieval for `scope=workspace`:

   ```sql
   SELECT
     f.chunk_id,
     bm25(f) AS score
   FROM rag_chunks_fts f
   JOIN rag_chunks c ON c.id = f.chunk_id
   JOIN rag_documents d ON d.id = c.document_id
   WHERE d.workspace_id = :workspace_id
     AND f MATCH :fts_query
   ORDER BY score
   LIMIT :k_lex;
   ```

   Example: lexical retrieval for `scope=session`:

   ```sql
   SELECT
     f.chunk_id,
     bm25(f) AS score
   FROM rag_chunks_fts f
   JOIN rag_chunks c ON c.id = f.chunk_id
   JOIN rag_documents d ON d.id = c.document_id
   JOIN rag_document_sessions s ON s.document_id = d.id
   WHERE s.session_id = :session_id
     AND f MATCH :fts_query
   ORDER BY score
   LIMIT :k_lex;
   ```

5. Fusion (RRF):

   * Combine lexical and vector ranks using Reciprocal Rank Fusion.
   * `score(d) = sum(1 / (rrf_k + rank_list(d)))`
   * Keep top `N_candidates` for rerank.

6. Reranking:

   * Default (MVP): hybrid heuristic rerank using fused RRF score plus lightweight constraints:

     * encourage source diversity (penalize repeated chunks from the same document),
     * prefer chunks with section titles (often higher signal),
     * optionally prefer more recent/active artifact when `scope=session`.
   * Optional (high-stakes queries): LLM rerank via OpenRouter (more expensive).
   * Note: cosine-only rerank is discouraged as the default when vector retrieval already uses cosine.

7. Build the prompt context:

   * Deduplicate overlapping chunks (same `document_id`, adjacent `chunk_index`).
   * Include citation metadata from `source_name` and `section_title`.
   * Limit the final context to a small number of chunks (6 to 10) and a max character/token budget.

8. Grounding check:

   * If no chunks or low relevance, mark `rag_grounded = false`.
   * The response should say evidence is insufficient and suggest next steps:

     * expand scope (session → workspace),
     * ask for specific keywords,
     * import the missing PDF.

## Runtime behavior (explicit)

RAG retrieval is automatic but conditional:

* It runs only when `rag.enabled` is true and the agentic node decides the user’s question needs retrieval.
* If the question is general chat or unrelated to indexed content, the subgraph skips retrieval and `rag_context` stays empty.
* If no documents are indexed for the selected scope, retrieval returns no results and the answer is generated without RAG context (optionally with a short disclaimer).

Example context block to inject into prompts:

```
<retrieved-context>
[1] {source_name} | {section_title}
{chunk_text}

[2] {source_name} | {section_title}
{chunk_text}
</retrieved-context>
```

## LangGraph integration (RAG subgraph coupled to main graph)

RAG runs as a subgraph that enriches state before the main prompt-producing nodes execute. This keeps the main graph readable and enables agentic decisions without duplicating logic in every node.

### State additions

Extend `core/graphs/open_canvas/state.py` with:

* `rag_enabled: Optional[bool]`
* `rag_scope: Optional[str]` ("session" or "workspace")
* `rag_query: Optional[str]`
* `rag_queries: Optional[list[str]]`
* `rag_should_retrieve: Optional[bool]`
* `rag_candidates: Optional[list[dict]]`
* `rag_context: Optional[str]`
* `rag_citations: Optional[list[dict]]`
* `rag_grounded: Optional[bool]`

Recommended additional fields (optional but useful in MVP):

* `rag_retrieval_debug: Optional[dict]` (counts, thresholds, top scores)
* `rag_selected_chunk_ids: Optional[list[str]]`

### Subgraph location

Create a dedicated RAG graph under `core/graphs/rag/graph.py` (and `core/graphs/rag/state.py` if you want a separate schema). The subgraph can use the shared `OpenCanvasState` so it can read `messages`, `session_id`, and write `rag_context`.

Agentic subgraph flow:

```
stateDiagram-v2
    [*] --> DecideRetrieve
    DecideRetrieve -->|skip| [*]
    DecideRetrieve --> SelectScope
    SelectScope --> RewriteQuery
    RewriteQuery --> HybridRetrieve
    HybridRetrieve --> FuseCandidates
    FuseCandidates --> Rerank
    Rerank --> BuildContext
    BuildContext --> GroundingCheck
    GroundingCheck --> [*]
```

Node responsibilities:

* `DecideRetrieve`: sets `rag_should_retrieve` and default `rag_scope` (LLM or heuristics).
* `SelectScope`: adjusts `rag_scope` based on message intent, active artifact state, and settings.
* `RewriteQuery`: builds `rag_queries` (1 to 3 variations).
* `HybridRetrieve`: runs lexical + vector retrieval per query, enforcing scope in SQL for FTS and in repository selection for embeddings.
* `FuseCandidates`: merges ranks with RRF and stores `rag_candidates`.
* `Rerank`: applies hybrid heuristic rerank (default) or optional LLM rerank to produce top chunks.
* `BuildContext`: formats `rag_context` and `rag_citations`.
* `GroundingCheck`: sets `rag_grounded` and prepares fallback guidance when evidence is weak.

### Coupling points in the main graph

In `core/graphs/open_canvas/graph.py`:

* Add a node `ragRetrieve` that points to the compiled RAG subgraph.
* Update routing so that when `generatePath` selects `replyToGeneralInput`, `generateArtifact`, or `rewriteArtifact`, you first run `ragRetrieve` and then route to the original node using `state.next`.
* Leave other routes (artifact updates, quick actions) unchanged to avoid unnecessary retrieval.

Example routing pattern:

```
generatePath --> ragRetrieve --> route_node --> replyToGeneralInput
generatePath --> ragRetrieve --> route_node --> generateArtifact
generatePath --> ragRetrieve --> route_node --> rewriteArtifact
```

### Prompt usage

In `reply_to_general_input`, `generate_artifact`, and optionally `rewrite_artifact`, append `state.rag_context` (if present) to the system prompt. If `rag_grounded` is false, include a short disclaimer and ask for more context.

### Config wiring

Add `session_id` and `workspace_id` to `RunnableConfig.configurable` in `ChatViewModel.send_message` so the subgraph can scope retrieval properly.

## UI integration

Replace the placeholder RAG settings page with real controls:

* `rag.enabled` (bool)
* `rag.scope` ("session" or "workspace")
* `rag.chunk_size_chars` (int)
* `rag.chunk_overlap_chars` (int)
* `rag.k_lex` (int)
* `rag.k_vec` (int)
* `rag.rrf_k` (int)
* `rag.max_candidates` (int)
* `rag.embedding_model` (string, optional)
* `rag.enable_query_rewrite` (bool)
* `rag.enable_llm_rerank` (bool)

Persist these in `SettingsViewModel` via `SettingsRepository` (same pattern as deep search settings).

## Implementation order

1. Add SQLite schema and `rag_repository.py` (including FTS scope-join queries).
2. Add chunking utilities.
3. Implement `rag_service.py` with indexing, hybrid retrieval, fusion, and hybrid heuristic rerank.
4. Add the RAG subgraph and extend `OpenCanvasState` with `rag_*` fields.
5. Wire the subgraph into `core/graphs/open_canvas/graph.py` and pass `session_id` and `workspace_id` in config.
6. Add agentic decision nodes (retrieve or not, scope, query rewrite, grounding check).
7. Replace the RAG settings placeholder page.
