# settings-configuration Specification

## Purpose
TBD - created by archiving change update-ui-attractor-parity. Update Purpose after archive.
## Requirements
### Requirement: Configuration Dialog Layout
The system SHALL provide a modal configuration dialog with a left sidebar and stacked content area matching the reference layout. The sidebar SHALL list categories in order: Models, Deep Research, RAG, Memory, Shortcuts, Theme.

#### Scenario: Open settings
- **WHEN** the user opens settings
- **THEN** the dialog displays the sidebar categories in the reference order and shows the Models page by default.

### Requirement: Configuration Dialog Actions
The configuration dialog SHALL provide Save and Cancel actions. Save SHALL persist changes and apply them to the running application, and Cancel SHALL discard unsaved changes.

#### Scenario: Save settings
- **WHEN** the user saves configuration changes
- **THEN** the updated settings persist and take effect immediately.

#### Scenario: Cancel settings
- **WHEN** the user cancels configuration changes
- **THEN** the application keeps the previous settings.

### Requirement: Functional Models and Theme Pages
The Models page SHALL allow editing the API key and selecting a default model, and those changes SHALL persist. The Theme page SHALL allow selecting theme mode, font family, window transparency, and keep-above behavior, and those changes SHALL persist and update the UI.

#### Scenario: Update model settings
- **WHEN** the user updates the API key or default model
- **THEN** the new values persist and are used for subsequent chats.

#### Scenario: Update theme settings
- **WHEN** the user changes theme mode, font, transparency, or keep-above
- **THEN** the UI updates to reflect the new theme settings.

### Requirement: Placeholder Pages
The Deep Research, Memory, and Shortcuts pages SHALL be accessible from the sidebar and SHALL display placeholder layouts consistent with the reference without altering application behavior.

#### Scenario: Placeholder navigation
- **WHEN** the user navigates to a placeholder page
- **THEN** the page renders placeholder content and does not modify settings or runtime behavior.

### Requirement: Shortcuts Configuration Page
The system SHALL provide a Shortcuts configuration page that lists available shortcut actions with their key sequences and descriptions, allows editing key sequences, and offers a reset to defaults option. Changes SHALL update the in-memory settings immediately and SHALL persist only when the user saves the configuration dialog.

#### Scenario: Edit shortcut binding
- **WHEN** the user edits a shortcut key sequence on the Shortcuts page
- **THEN** the new key sequence is shown in the list and becomes the pending setting value.

#### Scenario: Reset shortcuts
- **WHEN** the user resets shortcuts to defaults
- **THEN** the list shows the default key sequences for all actions.

### Requirement: RAG Settings Page
The configuration dialog SHALL provide a RAG settings page with controls for `rag.enabled`, `rag.scope`, `rag.chunk_size_chars`, `rag.chunk_overlap_chars`, `rag.k_lex`, `rag.k_vec`, `rag.rrf_k`, `rag.max_candidates`, `rag.embedding_model`, `rag.enable_query_rewrite`, `rag.enable_llm_rerank`, and `rag.index_text_artifacts`. Changes on this page SHALL persist and apply to subsequent indexing and retrieval behavior.

#### Scenario: Update RAG settings
- **WHEN** the user updates RAG settings and saves
- **THEN** the values persist and are used by the RAG pipeline.

