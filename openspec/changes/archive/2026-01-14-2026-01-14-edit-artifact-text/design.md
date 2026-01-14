# Design: Edit Artifact Text

## User Experience
1.  **View Mode (Default)**: User sees rendered Markdown. `QTextEdit` is read-only.
2.  **Enter Edit Mode**: User double-clicks anywhere on the rendered text.
    -   Widget switches to "Edit Mode".
    -   Header displays "Save" and "Cancel" buttons replacing (or alongside) navigation.
    -   Content area shows raw Markdown text (if `MarkdownViewer` supports switching or we replace widget).
        -   *Technical Detail*: `QTextEdit` used as `MarkdownViewer` can be set to `setReadOnly(False)`. However, `setMarkdown` renders HTML. Editing rendered HTML as Markdown is tricky in `QTextEdit`.
        -   *Alternative*: Switch the `QStackedWidget` to a `QPlainTextEdit` (or use the existing `CodeEditor` reused/configured for markdown) for editing raw text, or `setText(markdown)` on `QTextEdit` instead of `setMarkdown`.
        -   *Decision*: For simplicity and correctness, when entering edit mode, we should swap to a raw text editor view (like `QPlainTextEdit` or `CodeEditor` reused) containing the raw markdown, because editing rendered HTML in `QTextEdit` doesn't strictly preserve Markdown formatting.
        -   *Refined approach*: `ArtifactPanel` already has a `QStackedWidget`. We can add a generic `RawEditor` or reuse `CodeEditor` for the editing state of Text artifacts. Or simply toggle `MarkdownViewer` to display raw text via `setText` instead of `setMarkdown` and enable editing.

3.  **Save**: User clicks "Save".
    -   Content is captured from editor.
    -   `ArtifactCollection` is updated with new content for the *current* version (or creates a new version? Requirement says "modify displayed text", implying valid edit. Usually valid edits might be new versions, but "Save" implies in-place update or explicit save. I will assume in-place update of current active version for simplicity unless versioning is strictly immutable. Open Canvas usually allows branching. I'll stick to updating the current active artifact version in memory and saving collection).
    -   Repo saves to SQLite.
    -   UI reverts to View Mode (rendered markdown).

4.  **Cancel**: User clicks "Cancel" (or presses Esc).
    -   Discard changes.
    -   UI reverts to View Mode.

## Architectural Changes
-   **UI**:
    -   `ArtifactPanel`: Add state `is_editing`.
    -   `ArtifactPanel`: Add `Save`/`Cancel` buttons to header (initially hidden).
    -   `MarkdownViewer`: Override `mouseDoubleClickEvent` to emit `doubleClicked` signal.
    -   `ArtifactPanel`: Slot for `doubleClicked` -> `start_edit_mode()`.

-   **Data Flow**:
    -   `start_edit_mode()`: Load raw markdown into editor widget.
    -   `save_edits()`: Get text -> update `view_model._artifact` -> `view_model._artifact_repository.save_collection`.

## Trade-offs
-   *In-place vs New Version*: Updating in-place is simpler for "typo fixing". Creating new version is safer but might clutter version history if not careful. Given "Save" button, in-place update of the *current head* seems appropriate. If user goes back to v1 and edits, maybe that should branch? For now, updating the currently displayed version is the requested behavior.

## Security & Safety
-   Input sanitization: None required strictly for local app, but standard storage safety applies.
