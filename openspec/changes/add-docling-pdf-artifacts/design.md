## Context
Open Canvas currently stores a single `ArtifactV3` per session and renders artifacts with two fixed tabs (Text/Code). The new workflow requires multiple artifacts per session, PDF ingestion into Markdown via Docling, and export of artifacts to disk for reuse in a RAG pipeline.

## Goals / Non-Goals
- Goals:
  - Ingest PDFs via the chat "+" control and convert them to Markdown with Docling.
  - Support multiple artifacts per session with dynamic `Art_N` / `Code_N` tabs plus `New_Art` / `New_Code`.
  - Ensure chat-driven actions only update the currently displayed artifact.
  - Export all text/code artifacts to `/home/m/Documents/Artifacts/Articles` on session switch or app close.
- Non-Goals:
  - Vector embeddings, indexing, or search.
  - Non-PDF file ingestion.
  - PDF editing or annotation workflows.

## Decisions
- Artifact data model
  - Introduce an artifact collection model (e.g., `ArtifactCollectionV1`) that stores an ordered list of artifacts and the active artifact identifier/index.
  - Preserve each artifact's version history as-is (reuse `ArtifactV3` for versioned content).
  - Store per-artifact export metadata (export filename, source PDF name) in the collection to keep file paths stable across updates.
  - Backward compatibility: if stored JSON matches the legacy `ArtifactV3` shape, wrap it into a collection with a single artifact and mark it active.
- UI and selection
  - Replace the Text/Code tabs with a tab bar showing one tab per artifact plus `New_Art` and `New_Code` tabs.
  - Keep a single content area that toggles between Markdown viewer and code editor based on the active artifact type.
  - Tab labels use `Art_N` / `Code_N` numbering based on creation order per type.
- PDF ingestion
  - The chat input "+" opens a file dialog filtered to PDFs.
  - Conversion runs in a worker thread to avoid UI blocking.
  - A new text artifact is created with title from the PDF base filename and Markdown content from Docling.
- Export strategy
  - Export on session switch and app close (matching requirements), writing `.md` files into `/home/m/Documents/Artifacts/Articles` and creating the directory if missing.
  - For PDF ingestions, use the PDF base filename and append `-2`, `-3`, etc. if a file already exists to guarantee a new file per ingestion.
  - For chat-created artifacts, use `{session_title}-{tab_label}.md` and overwrite the existing file on update.
  - Code artifacts export as fenced Markdown using the artifact language when available.
- Action scoping
  - Chat graph state uses the active artifact only; updates are applied back to that artifact within the collection.

## Alternatives considered
- Retaining the Text/Code tabs and adding a separate artifact list: rejected to match the requested tab-based workflow.
- Exporting on every artifact change: rejected because requirements specify session switch and app close.
- Using alternate PDF parsers (pdfplumber, pypdf): rejected because Docling is required.

## Risks / Trade-offs
- Docling conversion latency for large PDFs; requires background processing and clear UI status handling.
- Migration complexity for stored artifact JSON.
- File naming collisions for PDFs; addressed with numeric suffixing.
- Session title changes can alter export filenames for chat artifacts; export should use the current title at export time.

## Migration Plan
- On load, detect legacy `ArtifactV3` JSON and wrap into a collection with a single artifact and active index 0/1.
- On save, always persist the new collection shape to the artifacts table.

## Open Questions
- None.
