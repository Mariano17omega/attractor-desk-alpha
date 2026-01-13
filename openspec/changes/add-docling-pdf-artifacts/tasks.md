## 1. Data model and persistence
- [x] 1.1 Define the artifact collection model and update type definitions for multi-artifact storage.
- [x] 1.2 Update artifact persistence to read/write the new collection shape with backward compatibility.

## 2. PDF ingestion via Docling
- [x] 2.1 Add a Docling conversion service (background thread) that returns Markdown.
- [x] 2.2 Wire the chat "+" control to open a PDF picker and create a new text artifact from Docling output.
- [x] 2.3 Surface conversion errors in the UI status/error channel.

## 3. Artifact tabs and selection
- [x] 3.1 Replace Text/Code tabs with dynamic `Art_N` / `Code_N` tabs plus `New_Art` / `New_Code`.
- [x] 3.2 Implement blank artifact creation and active artifact selection.
- [x] 3.3 Scope chat-driven artifact updates to the active artifact only.

## 4. Artifact export to disk
- [x] 4.1 Implement artifact export formatting for text and code artifacts.
- [x] 4.2 Export artifacts to `/home/m/Documents/Artifacts/Articles` on session switch and app close, enforcing naming rules.

## 5. Validation
- [x] 5.1 Add tests for artifact collection persistence and export naming/formatting.
- [x] 5.2 Add tests or mocks for the PDF ingestion flow.
- [x] 5.3 Run `openspec validate add-docling-pdf-artifacts --strict`.

