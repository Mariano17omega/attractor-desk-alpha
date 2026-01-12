# settings-configuration Specification Delta

## ADDED Requirements
### Requirement: RAG Settings Page
The configuration dialog SHALL provide a RAG settings page with controls for `rag.enabled`, `rag.scope`, `rag.chunk_size_chars`, `rag.chunk_overlap_chars`, `rag.k_lex`, `rag.k_vec`, `rag.rrf_k`, `rag.max_candidates`, `rag.embedding_model`, `rag.enable_query_rewrite`, `rag.enable_llm_rerank`, and `rag.index_text_artifacts`. Changes on this page SHALL persist and apply to subsequent indexing and retrieval behavior.

#### Scenario: Update RAG settings
- **WHEN** the user updates RAG settings and saves
- **THEN** the values persist and are used by the RAG pipeline.

## MODIFIED Requirements
### Requirement: Placeholder Pages
The Deep Research, Memory, and Shortcuts pages SHALL be accessible from the sidebar and SHALL display placeholder layouts consistent with the reference without altering application behavior.

#### Scenario: Placeholder navigation
- **WHEN** the user navigates to a placeholder page
- **THEN** the page renders placeholder content and does not modify settings or runtime behavior.
