## ADDED Requirements
### Requirement: Mode-aware RAG routing
The system SHALL add `global_rag_node` and `local_rag_node` and route between them based on conversation state: ChatPDF mode (or presence of an active session PDF) SHALL activate `local_rag_node` and skip `global_rag_node`; normal mode SHALL activate `global_rag_node` and skip `local_rag_node`. Each node SHALL emit which path ran and SHALL be positioned before response-generation nodes.

#### Scenario: Route to local in ChatPDF
- **WHEN** the conversation is in ChatPDF mode and retrieval is needed
- **THEN** the graph executes `local_rag_node`, skips `global_rag_node`, and returns local context before the response node runs.

#### Scenario: Route to global in normal chat
- **WHEN** the conversation is in normal mode and retrieval is needed
- **THEN** the graph executes `global_rag_node`, skips `local_rag_node`, and returns global context before the response node runs.

### Requirement: Retrieval metadata and debug logging
The system SHALL record which RAG source was used (`rag_used = global|local`), the scope queried, and candidate/context counts for each run. Nodes SHALL log which path was activated and why, and responses SHALL carry metadata indicating whether global or local RAG grounded the answer.

#### Scenario: Metadata on reply
- **WHEN** a response is generated after RAG
- **THEN** the state includes `rag_used`, scope, and retrieval debug info
- **AND** logs show which node ran and the reason (e.g., "mode=chatpdf -> local_rag_node").

## MODIFIED Requirements
### Requirement: Scope Enforcement
The system SHALL support session, workspace, and global retrieval scopes and enforce scope at SQL time for FTS queries using joins to `rag_documents` and `rag_document_sessions`. Vector retrieval SHALL only scan embeddings within the selected scope. Global scope SHALL query only documents with `workspace_id = "GLOBAL"`. ChatPDF local retrieval SHALL always use the current `session_id` scope. Results MUST NOT be post-filtered in Python after ranking.

#### Scenario: Session-scoped retrieval
- **WHEN** the scope is set to session and the user asks a question
- **THEN** only chunks linked to the session are eligible for retrieval.

#### Scenario: Global-scoped retrieval
- **WHEN** the scope is set to global and the user asks a question
- **THEN** only chunks from documents stored under `workspace_id = "GLOBAL"` are eligible for retrieval.

### Requirement: Graph and Prompt Integration
The system SHALL run a dedicated RAG subgraph before response-generation nodes and populate `rag_*` state fields used by downstream prompts. The system SHALL pass `session_id`, `workspace_id`, `conversation_mode`, and `rag_scope` via the runnable configuration for scoping. Prompt-producing nodes SHALL append `rag_context` when present, include a short disclaimer when `rag_grounded` is false, and MAY include which RAG source (`rag_used`) supplied the context for transparency.

#### Scenario: RAG subgraph runs before reply
- **WHEN** the graph routes to a response-generation node
- **THEN** the RAG subgraph executes first (selecting global or local) and enriches the state used by the prompt, including `rag_used` and `rag_context`.
