# Proposal: Edit Artifact Text

## Summary
Allow users to manually edit artifact text by double-clicking the content, making adjustments, and saving changes. This provides a quick way to fix minor issues or tweak content without engaging the AI.

## Business Value
- **User Agency**: Users can directly correct errors or style preferences without explaining them to an AI.
- **Efficiency**: Faster than explaining a small change to the LLM.
- **Data Integrity**: Ensures artifacts accurately reflect the user's intent.

## Scope
-   **In Scope**:
    -   Double-click to edit text artifacts in existing `ArtifactPanel`.
    -   "Save" button to persist changes.
    -   "Cancel" or explicit exit from edit mode (revert).
    -   Read-only vs. Edit mode toggling.
    -   Updating the in-memory `ArtifactV3` model and persisting via `ArtifactRepository`.

-   **Out of Scope**:
    -   Real-time collaborative editing.
    -   Rich text editor toolbar (plain markdown text edit is sufficient).
    -   Editing code artifacts (initially scoped to text/markdown, though code editor already exists/is editable? CodeEditor is `QPlainTextEdit` but currently treated as read-only or display-only in flow). *Correction*: The user request specifically mentions "artifact text", implying text artifacts. I will enable it for text artifacts first as requested. *Refinement*: The request says "artifact text" broadly. Doing it for both if easy is good, but `MarkdownViewer` and `CodeEditor` are separate widgets. I will focus on `MarkdownViewer` as per "text" implication, but the design should allow for code editing too if `CodeEditor` supports it easily.

## Dependencies
-   `ui.widgets.artifact_panel.ArtifactPanel`
-   `core.persistence.artifact_repository.ArtifactRepository`
