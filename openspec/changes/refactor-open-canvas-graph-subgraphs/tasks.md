## 1. Implementation
- [x] 1.1 Add `artifact_action`, optional `artifact_action_params`, and a recovery message field to `OpenCanvasState`; update `clean_state` to clear them.
- [x] 1.2 Update `generate_path` and web-search routing to set `artifact_action` and route to `artifactOps` while preserving existing route behavior.
- [x] 1.3 Create the ArtifactOps subgraph with `artifactActionDispatch`, action routing, and `generateFollowup` inside the subgraph.
- [x] 1.4 Update the main OpenCanvas graph to replace direct artifact-action edges with the ArtifactOps subgraph entry.
- [x] 1.5 Update `replyToGeneralInput` to return a deterministic recovery message when dispatch sets it.

## 2. Tests
- [x] 2.1 Add unit tests for `artifactActionDispatch` (missing artifact, missing highlight, invalid action).
- [x] 2.2 Add unit tests for ArtifactOps subgraph invocation (generate/rewrite/update paths).
- [x] 2.3 Add regression test for web search routing preserving `artifact_action`.

## 3. Documentation
- [x] 3.1 Create `Documentation/architecture/langgraph-open-canvas.md` with the updated diagrams and narrative.
- [x] 3.2 Update `report.md` to reference the new architecture doc and include a short overview diagram.

## 4. Validation
- [x] 4.1 Run `pytest` for the new/updated tests.
