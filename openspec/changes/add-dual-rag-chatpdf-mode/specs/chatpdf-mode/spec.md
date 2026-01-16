## ADDED Requirements
### Requirement: ChatPDF mode activation and state
The system SHALL expose `conversation_mode` (`normal`|`chatpdf`) and `active_pdf_document_id` in graph state. Loading a PDF into ChatPDF mode SHALL set `conversation_mode = chatpdf`, set `active_pdf_document_id`, and disable the global RAG node. Returning to normal chat SHALL clear `active_pdf_document_id`, set `conversation_mode = normal`, and re-enable the global RAG node. The state SHALL track which RAG nodes are active for downstream routing and debugging.

#### Scenario: Switch modes
- **WHEN** the user opens a PDF in ChatPDF mode
- **THEN** the state switches to `chatpdf`, records the active PDF document id, and routes retrieval to local only
- **AND** when the user exits ChatPDF, the state resets to `normal` and routes retrieval back to global.

### Requirement: PDF viewer artifact creation
The system SHALL create a non-editable `ArtifactType.PDF_VIEWER` when a PDF is uploaded in chat, storing `pdf_path`, `total_pages`, `current_page`, and `rag_document_id` metadata. The PDF SHALL be saved to the session’s temp directory, a new artifact tab SHALL open automatically with the viewer, and local RAG indexing SHALL start in the background. The UI SHALL show an "Indexing..." indicator until local indexing completes or fails.

#### Scenario: Upload PDF in ChatPDF
- **WHEN** the user uploads a PDF
- **THEN** a PDF viewer artifact is created and opened in a new tab with metadata populated
- **AND** the file is saved to the session temp directory and local indexing starts with an "Indexing..." status shown until ready.

### Requirement: PDF viewer controls
The PDF viewer widget SHALL provide zoom in/out, previous/next page, and go-to-page controls; optionally, it MAY expose a thumbnails sidebar toggle. It SHALL display the current page status (e.g., "Page 5 of 42") and honor the stored `current_page` when re-opened. The viewer SHALL remain read-only.

#### Scenario: Navigate PDF viewer
- **WHEN** the user uses navigation controls in the PDF viewer
- **THEN** the displayed page updates, the page status reflects the new position, and the viewer re-opens to the last viewed page on revisit.
