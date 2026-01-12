# rag-retrieval Specification Delta

## ADDED Requirements
### Requirement: Conditional Retrieval
The system SHALL run RAG retrieval only when `rag.enabled` is true and the agentic decision indicates retrieval is needed. When retrieval is skipped, the system SHALL leave `rag_context` empty.

#### Scenario: General chat skips retrieval
- **WHEN** the user sends a general chat message and retrieval is not needed
- **THEN** the response is generated without RAG context.

### Requirement: Scope Enforcement
The system SHALL support session and workspace retrieval scopes and enforce scope at SQL time for FTS queries using joins to `rag_documents` and `rag_document_sessions`. Vector retrieval SHALL only scan embeddings within the selected scope. Results MUST NOT be post-filtered in Python after ranking.

#### Scenario: Session-scoped retrieval
- **WHEN** the scope is set to session and the user asks a question
- **THEN** only chunks linked to the session are eligible for retrieval.

### Requirement: Query Rewrite
When `rag.enable_query_rewrite` is enabled, the system SHALL generate one to three rewritten queries to improve recall. When disabled, the system SHALL use the original user query only.

#### Scenario: Query rewrite enabled
- **WHEN** query rewrite is enabled for a user question
- **THEN** the retrieval stage uses the original query plus rewrites.

### Requirement: Hybrid Retrieval and Fusion
For each query, the system SHALL run FTS5 lexical retrieval and vector retrieval when embeddings are available, keeping the top K results per method. The system SHALL fuse results with Reciprocal Rank Fusion (RRF) using a configurable `rag.rrf_k` and select the top N candidates for reranking. If embeddings are unavailable or disabled, the system SHALL proceed with lexical retrieval only.

#### Scenario: Embeddings disabled
- **WHEN** embeddings are disabled for a query
- **THEN** lexical retrieval runs and fused candidates are based on lexical results only.

### Requirement: Reranking and Context Building
The system SHALL apply heuristic reranking by default (source diversity, section title preference, and session recency). When `rag.enable_llm_rerank` is enabled and an API key is configured, the system SHALL allow LLM reranking. The system SHALL build a context block with citations, deduplicate adjacent chunks within the same document, and respect max chunk count and budget settings. When no relevant chunks are found, the system SHALL set `rag_grounded` to false and provide guidance to expand scope or add documents.

#### Scenario: Build grounded context
- **WHEN** relevant chunks are found for a query
- **THEN** the system emits a bounded context block with citations and `rag_grounded` set to true.

### Requirement: Graph and Prompt Integration
The system SHALL run a dedicated RAG subgraph before response-generation nodes and populate `rag_*` state fields used by downstream prompts. The system SHALL pass `session_id` and `workspace_id` via the runnable configuration for scoping. Prompt-producing nodes SHALL append `rag_context` when present and include a short disclaimer when `rag_grounded` is false.

#### Scenario: RAG subgraph runs before reply
- **WHEN** the graph routes to a response-generation node
- **THEN** the RAG subgraph executes first and enriches the state used by the prompt.
