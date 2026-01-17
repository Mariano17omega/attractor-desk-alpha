## Context
The OpenCanvas graph in `core/graphs/open_canvas/graph.py` currently wires many artifact actions directly from the main graph, while also handling web search, RAG, followups, and housekeeping. Routing uses `next` for both graph traversal and artifact action selection. Artifact mutation nodes perform their own precondition checks and raise when prerequisites are missing. Web search uses `post_web_search_route` to return to the intended node. This creates a dense routing map that is difficult to reason about and test in isolation.

## Goals / Non-Goals
- Goals:
  - Make graph phases explicit: routing, contextualization (RAG/web), artifact operations, and housekeeping.
  - Move all artifact mutation actions into a dedicated ArtifactOps subgraph.
  - Centralize artifact action validation and recovery messaging.
  - Preserve current behavior for existing routes (updateArtifact, rewriteArtifactTheme, rewriteCodeArtifactTheme, updateHighlightedText, customAction, webSearch, imageProcessing, replyToGeneralInput).
  - Enable unit tests that invoke ArtifactOps and RAG subgraphs directly with minimal state.
- Non-Goals:
  - Change LLM prompts, models, or artifact schemas.
  - Alter RAG ranking logic or web search provider behavior.
  - Redesign UI or persistence flows.

## Decisions
- Decision: Create a dedicated ArtifactOps subgraph with a single entry node `artifactActionDispatch`.
  - Why: A single entry point allows centralized validation, eliminates duplicated precondition checks, and clarifies which nodes can mutate `state.artifact`.
  - Notes: The subgraph will contain `generateArtifact`, `rewriteArtifact`, `updateArtifact`, `updateHighlightedText`, `rewriteArtifactTheme`, `rewriteCodeArtifactTheme`, `customAction`, and `generateFollowup`, and then end.

- Decision: Add `artifact_action` (and optional `artifact_action_params`) to `OpenCanvasState` and keep `next` strictly for graph routing.
  - Why: Separates routing intent from action selection and simplifies post-web-search continuation.
  - Notes: `generate_path` and web-search routing will set `artifact_action` while routing to `artifactOps`. The action value will persist across `webSearch` and `routePostWebSearch` without overloading `next`.

- Decision: Add a recovery message field (for example, `artifact_action_recovery_message`) consumed by `replyToGeneralInput`.
  - Why: Enables deterministic, user-friendly guidance when prerequisites are missing without invoking the LLM.
  - Notes: `artifactActionDispatch` will set this field and route to `replyToGeneralInput` for soft failures.

- Decision: Validation and recovery policy in `artifactActionDispatch`.
  - Why: The user requires soft-fail guidance for missing prerequisites and a hard-fail for invariant violations.
  - Notes:
    - Missing artifact or highlight selection triggers a soft-fail: route to `replyToGeneralInput` with a short guidance message and log a structured warning.
    - Unknown action key or invalid artifact structure triggers a hard-fail: log a structured error and raise a user-safe exception for the UI to surface without a stack trace.

- Decision: Keep RAG as a dedicated subgraph and treat it as a single contextualization module.
  - Why: Preserves existing RAG boundaries while making the phase explicit in the main graph.

## Risks / Trade-offs
- Additional state fields require careful clearing in `clean_state` to avoid stale actions or recovery messages.
- Centralized dispatch can introduce regressions if action routing is incomplete; mitigate with targeted unit tests.
- Deterministic recovery messages bypass LLM output; ensure they are concise and clear.

## Migration Plan
1. Add new state fields and update `clean_state` to clear them.
2. Introduce the ArtifactOps subgraph and dispatch node.
3. Update the main graph routing to use ArtifactOps and preserve RAG/web search flows.
4. Update `replyToGeneralInput` to honor recovery messages.
5. Add tests for ArtifactOps and routing continuity.
6. Update Mermaid diagrams and architecture documentation.

## Open Questions
- None.
