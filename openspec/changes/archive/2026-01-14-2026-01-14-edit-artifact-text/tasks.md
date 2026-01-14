# Tasks: Edit Artifact Text

- [x] Implement `EditableMarkdownViewer` or modify `MarkdownViewer` to support double-click signal.
- [x] Update `ArtifactPanel` layout to include "Save" and "Cancel" buttons (initially hidden).
- [x] Implement `start_edit_mode` logic:
    - [x] Hide version nav, show Save/Cancel.
    - [x] Switch content view to raw text editor (or toggle rendering).
- [x] Implement `save_edit_mode` logic:
    - [x] Capture text.
    - [x] Update `ArtifactV3` object in `ChatViewModel`.
    - [x] specific persistence call.
    - [x] Re-render and exit edit mode.
- [x] Verify double-click enters edit mode.
- [x] Verify Save persists changes locally.
- [x] Verify Cancel discards changes.
