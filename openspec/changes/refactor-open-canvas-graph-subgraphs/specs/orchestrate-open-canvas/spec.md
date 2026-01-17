## ADDED Requirements
### Requirement: Phased OpenCanvas Orchestration
The system SHALL organize the OpenCanvas graph into explicit phases: routing, contextualization, artifact operations, and housekeeping. The main graph SHALL enter contextualization through the RAG subgraph and enter artifact operations through the ArtifactOps subgraph before running housekeeping nodes.

#### Scenario: Artifact change follows phased routing
- **WHEN** the user request results in an artifact mutation action
- **THEN** the graph routes from `generatePath` through contextualization (RAG/web search as configured) into `artifactOps` before `reflect` and `cleanState`.

### Requirement: ArtifactOps Subgraph Boundaries
All artifact mutation operations (`generateArtifact`, `rewriteArtifact`, `updateArtifact`, `updateHighlightedText`, `rewriteArtifactTheme`, `rewriteCodeArtifactTheme`, `customAction`) SHALL execute inside the ArtifactOps subgraph, and `generateFollowup` SHALL execute inside the subgraph after the mutation.

#### Scenario: Artifact mutation occurs only inside ArtifactOps
- **GIVEN** an `updateArtifact` request
- **WHEN** the OpenCanvas graph runs
- **THEN** the artifact update happens within the ArtifactOps subgraph
- **AND** no other main-graph node mutates `state.artifact`.

### Requirement: Artifact Action Dispatch and Recovery
ArtifactOps SHALL begin with `artifactActionDispatch`, which reads `artifact_action`, validates prerequisites, and routes to the selected action. For user-correctable missing prerequisites, the system SHALL route to `replyToGeneralInput` with an explicit recovery message, SHALL log a structured warning, and SHALL NOT auto-generate artifacts. For invalid action keys or invalid artifact structure, the system SHALL fail the run with a user-safe error message and log a structured error.

#### Scenario: Missing artifact for rewrite
- **GIVEN** `artifact_action` is `rewriteArtifact` and no active artifact exists
- **WHEN** `artifactActionDispatch` runs
- **THEN** the system routes to `replyToGeneralInput` with a message asking the user to select/create an artifact or confirm generation
- **AND** the system logs a structured warning.

#### Scenario: Missing highlighted selection
- **GIVEN** `artifact_action` is `updateHighlightedText` and no highlighted selection exists
- **WHEN** `artifactActionDispatch` runs
- **THEN** the system routes to `replyToGeneralInput` with a message requesting a highlighted selection
- **AND** the system logs a structured warning.

#### Scenario: Invalid action key
- **GIVEN** `artifact_action` is unrecognized
- **WHEN** `artifactActionDispatch` runs
- **THEN** the system fails with a user-safe error message
- **AND** the system logs a structured error.

### Requirement: Separate Routing and Artifact Action State
The system SHALL store graph routing decisions in `next` and artifact operation selection in `artifact_action` (and optional `artifact_action_params`). Web search routing SHALL preserve `artifact_action` so that the post-web-search path resumes the intended artifact operation.

#### Scenario: Web search preserves artifact action
- **GIVEN** a user request triggers web search and an artifact mutation
- **WHEN** the graph completes `webSearch` and `routePostWebSearch`
- **THEN** the graph routes to `artifactOps` and uses the original `artifact_action` value.

### Requirement: Subgraph Testability
The system SHALL expose the ArtifactOps subgraph as a standalone compiled graph that can be invoked with a minimal `OpenCanvasState` and configuration for unit tests.

#### Scenario: ArtifactOps invoked in isolation
- **GIVEN** a minimal state with `artifact_action` set to `generateArtifact` and a user message
- **WHEN** the ArtifactOps subgraph is invoked directly
- **THEN** it produces an artifact update and a followup message without requiring the main graph.
