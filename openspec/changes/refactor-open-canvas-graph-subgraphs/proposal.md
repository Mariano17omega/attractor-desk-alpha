# Change: Refactor OpenCanvas graph into explicit subgraphs

## Why
The current OpenCanvas graph mixes routing, contextualization, artifact mutations, and housekeeping in a single graph with many direct edges. This makes the flow harder to understand, maintain, and test. The requested refactor introduces explicit phase boundaries and a dedicated ArtifactOps subgraph with centralized validation, improving readability and unit testability without changing user-visible behavior.

## What Changes
- Introduce an ArtifactOps subgraph with a single entry point and an `artifactActionDispatch` node that validates prerequisites and selects the artifact action.
- Add `artifact_action` (plus optional `artifact_action_params`) to `OpenCanvasState` to separate routing decisions from artifact operations; add a recovery message field to support explicit user guidance on soft failures.
- Rework the main OpenCanvas graph to route artifact operations through the ArtifactOps subgraph, keep RAG as a standalone contextualization subgraph, and keep housekeeping (`reflect`, `cleanState`, `generateTitle`, `summarizer`) outside.
- Preserve web search routing behavior while ensuring the artifact action survives the web search hop.
- Update Mermaid diagrams in `report.md` and add a canonical architecture doc under `Documentation/architecture/`.

## Impact
- Affected specs: `orchestrate-open-canvas` (new capability), references to `rag-retrieval` and `web-search` (behavior preserved).
- Affected code: `core/graphs/open_canvas/graph.py`, `core/graphs/open_canvas/state.py`, `core/graphs/open_canvas/nodes/generate_path.py`, `core/graphs/open_canvas/nodes/reply_to_general_input.py`, `core/graphs/open_canvas/nodes/clean_state.py`, new ArtifactOps subgraph module under `core/graphs/open_canvas/`.
- Affected docs: `report.md`, `Documentation/architecture/langgraph-open-canvas.md`.
