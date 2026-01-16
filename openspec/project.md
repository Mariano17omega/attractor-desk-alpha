# Project Context

## Purpose
**Version**: 0.3.0 (Alpha)

Attractor Desk is a native Python desktop application for AI-assisted writing and coding. It evolves the original [Open Canvas](https://github.com/langchain-ai/open-canvas) concept into a local-first, desktop experience where users collaborate with an AI to create and iteratively refine "artifacts" side-by-side with a chat interface. The app emphasizes persistent workspaces, artifact versioning, and optional local RAG for context grounding.

## Tech Stack
- **Languages**: Python 3.11+
- **Packaging**: `pyproject.toml` with setuptools; CLI entrypoint `attractor-desk` -> `ui.main:main`
- **UI Framework**: PySide6 (Qt for Python), QSS theming in `ui/styles.py`
- **Agent/LLM Orchestration**: LangGraph + LangChain; LangSmith tracing is optional
- **LLM Provider**: OpenRouter via a custom `OpenRouterChat` wrapper (httpx, streaming, tool calls)
- **Embeddings**: OpenRouter embeddings (`openai/text-embedding-3-small` default)
- **RAG**: SQLite FTS5 + in-process cosine similarity + RRF fusion; optional LLM rerank
- **Search/Scraping**: Exa search + Firecrawl scraping (optional extras)
- **PDF Ingestion**: Docling (optional extra for PDF to Markdown)
- **Screen Capture**: mss for full-screen/region capture
- **Persistence**: SQLite via `core/persistence` (WAL) and JSON-serialized artifacts
- **Testing**: pytest, pytest-asyncio
- **Utilities**: Pydantic (LLM and artifact types), dataclasses for persisted domain models

## Project Conventions

### Code Style
- **Formatter**: Black (line length 100)
- **Linter**: Ruff (select E/F/I/W, ignore E501)
- **Type Checking**: Mypy (warn_return_any, warn_unused_ignores, ignore_missing_imports)
- **Naming**: snake_case for functions/variables, PascalCase for classes

### Spec-Driven Development
- **Workflow**: Follows the OpenSpec standard (see `openspec/AGENTS.md`) for all non-trivial changes.
- **Source of Truth**: `openspec/specs/` contains the current system requirements.
- **Proposals**: New features start as proposals in `openspec/changes/<change-id>/`.
- **Validation**: Run `openspec validate` before implementation and archiving.

### Architecture Patterns
- **MVVM (Model-View-ViewModel)**: UI logic in `ui/viewmodels` emits Qt signals to widgets in `ui/widgets`.
- **Core/UI Separation**:
    - `core/`: Business logic, graph orchestration, providers, persistence, and types. No UI dependencies.
    - `ui/`: PySide6 UI, viewmodels, and widgets.
    - `openspec/`: Project specifications, change proposals, and agent instructions.
- **LangGraph Graphs**:
    - Main graph in `core/graphs/open_canvas/graph.py`. Most nodes are in `core/graphs/open_canvas/nodes`, but some lightweight nodes (like `webSearch`, `summarizer`, `generateTitle`) are defined directly in `graph.py`.
    - RAG subgraph in `core/graphs/rag/graph.py`.
- **Repositories**: SQLite repositories in `core/persistence` wrap DB access.
- **Services**: PDF conversion and artifact export live in `core/services`.
- **Threading**: Graph execution, PDF conversion, and RAG indexing run in `QThread` workers to keep UI responsive.
- **Settings**: `SettingsViewModel` owns user-configurable options and persists to SQLite via `SettingsRepository`. API keys (except LangSmith) are stored securely in the OS keyring via `KeyringService`; LangSmith keys are dev-only and read from environment variables or `API_KEY.txt`.

### Data and Persistence
- **SQLite**: Default DB at `~/.attractor_desk/database.db` (WAL) with tables for workspaces, sessions, messages, message_attachments, artifacts, RAG, and settings.
- **Artifacts**: Stored as `ArtifactCollectionV1` JSON with versioned `ArtifactV3` contents and export metadata. Includes `ArtifactPdfV1` for PDF artifacts in ChatPDF mode.
- **Export**: Artifacts export to `~/Documents/Artifacts/Articles` via `ArtifactExportService`.
- **Attachments**: Message attachments store file paths in SQLite; images are injected into chat payloads as data URLs. Screenshots are saved to `~/Documents/Attractor_Imagens`.
- **RAG Storage**: `rag_documents`, `rag_chunks`, `rag_chunks_fts`, and `rag_embeddings` live in SQLite. Each ChatPDF session gets its own isolated RAG scope.
- **Settings**: Stored in SQLite; API keys (OpenRouter, Exa, Firecrawl) are stored in the OS keyring (Keychain/Secret Service/Credential Locker) with fallback to environment variables. LangSmith API keys are intentionally excluded from keyring storage (dev-only) and read from environment variables or `API_KEY.txt`.
- **Store**: LangGraph uses an in-memory store in `core/store` for reflections (non-persistent).
- **Secure Storage**: `keyring>=25.0.0` for OS-level credential storage with migration support for legacy `API_KEY.txt` files.

### Testing Strategy
- **Unit Tests**: pytest for core logic, persistence, RAG, providers, and viewmodels.
- **Async Testing**: pytest-asyncio with `asyncio_mode=auto`.

### Git Workflow
- Feature branches and PRs (per README contributing notes).
- Semantic versioning.

## Domain Context
- **Workspaces and Sessions**: Workspaces contain sessions, sessions contain messages and artifact collections.
- **Artifacts**: Text or code; multi-artifact tabs in the UI (+ Art / + Code) with version navigation and export on app close. Markdown content is rendered in message bubbles.
- **ChatPDF**: Dedicated mode for PDF interaction with:
  - Native PySide6 `PdfViewerWidget` for in-app PDF rendering
  - Isolated RAG scope per uploaded PDF (separate from Global RAG)
  - PDF content parsed via Docling, chunked, and embedded into a ChatPDF-specific vector database
  - Questions answered exclusively from the uploaded PDF content
  - `ArtifactPdfV1` artifact type for PDF metadata and file path storage
- **RAG Architecture**: 
  - **Global RAG**: Available in all sessions except ChatPDF; indexes text artifacts and manually imported documents from a configurable folder path
  - **ChatPDF RAG**: Isolated, per-PDF RAG scope active only in ChatPDF sessions; never combined with Global RAG
  - SQLite FTS5 + in-process cosine similarity + RRF fusion; optional LLM rerank for retrieval
- **Image Processing**: The `imageProcessing` node handles image attachments, preparing them for multimodal models or subsequent steps. Screenshots are captured via `mss` and saved locally.
- **Deep Search**: UI toggle and settings for Exa/Firecrawl. The `web_search_node` dynamically classifies queries, generates search terms, and injects results into downstream nodes.
- **Routing**: The graph routes based on explicit state flags (highlighted text/code, quick actions) and LLM-based intent decisions.
- **Streaming**: OpenRouter streaming drives responsive updates in the UI.
- **Defaults**: Default model is `anthropic/claude-3.5-sonnet`; separate configurable `image_model` for multimodal processing (screenshots, image attachments).

## Important Constraints
- **Qt Threading**: Graph execution and PDF conversion run off the main UI thread (QThread) to avoid freezes.
- **Configuration**: `OPENROUTER_API_KEY` is required (stored in OS keyring or environment variable). Exa and Firecrawl keys are optional (stored in keyring). LangSmith key is dev-only and intentionally NOT stored in keyring—read from environment or `API_KEY.txt`.
- **Image Attachments**: Screen captures are saved to `/home/m/Documents/Attractor_Imagens`; images attach only if the model supports vision.
- **Functional Nodes**: Summarizer, title generation, and web search nodes are fully implemented. Summarizer runs when messages exceed token budget; title generation triggers after the first human-AI exchange.

## External Dependencies
- **OpenRouter API**: Required LLM backend.
- **LangSmith**: Optional tracing.
- **Exa + Firecrawl**: Optional deep search and scraping.
- **Docling**: Optional PDF to Markdown conversion.
