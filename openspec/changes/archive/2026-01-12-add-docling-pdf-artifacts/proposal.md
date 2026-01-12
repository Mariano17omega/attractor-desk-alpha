# Change: Add Docling PDF ingestion and multi-artifact tabs

## Why
- Users need to ingest PDFs into reusable Markdown artifacts for downstream RAG preprocessing and keep them alongside chat artifacts.
- The current artifact model and UI only support a single artifact with text/code tabs, which blocks multi-document workflows.

## What Changes
- Add a Docling-based PDF ingestion flow from the chat "+" control that creates a new text artifact and makes it active.
- Expand artifact storage to support multiple artifacts per session with dynamic tabs and blank artifact creation.
- Scope chat-driven artifact updates to the currently selected artifact only.
- Export artifacts to `/home/m/Documents/Artifacts/Articles` on session switch and app close using the required naming conventions.

## Impact
- Affected specs: new `ingest-pdf-documents`, new `manage-artifacts`, new `export-artifacts`, modified `manage-chat-sessions`.
- Affected code: `ui/widgets/chat_panel.py`, `ui/widgets/artifact_panel.py`, `ui/viewmodels/chat_viewmodel.py`, `ui/viewmodels/main_viewmodel.py`, `core/types.py`, `core/persistence/artifact_repository.py`, `ui/main_window.py`, plus new core services.
