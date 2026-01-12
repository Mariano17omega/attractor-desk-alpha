# Project Context

## Purpose
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

### Architecture Patterns
- **MVVM (Model-View-ViewModel)**: UI logic in `ui/viewmodels` emits Qt signals to widgets in `ui/widgets`.
- **Core/UI Separation**:
    - `core/`: Business logic, graph orchestration, providers, persistence, and types. No UI dependencies.
    - `ui/`: PySide6 UI, viewmodels, and widgets.
- **LangGraph Graphs**:
    - Main graph in `core/graphs/open_canvas/graph.py` with nodes in `core/graphs/open_canvas/nodes`.
    - RAG subgraph in `core/graphs/rag/graph.py`.
- **Repositories**: SQLite repositories in `core/persistence` wrap DB access.
- **Services**: PDF conversion and artifact export live in `core/services`.
- **Threading**: Graph execution, PDF conversion, and RAG indexing run in `QThread` workers to keep UI responsive.
- **Settings**: `SettingsViewModel` owns user-configurable options and persists to SQLite via `SettingsRepository`.

### Data and Persistence
- **SQLite**: Default DB at `~/.open_canvas/database.db` (WAL) with tables for workspaces, sessions, messages, message_attachments, artifacts, RAG, and settings.
- **Artifacts**: Stored as `ArtifactCollectionV1` JSON with versioned `ArtifactV3` contents and export metadata.
- **Export**: Artifacts export to `~/Documents/Artifacts/Articles` via `ArtifactExportService`.
- **Attachments**: Message attachments store file paths in SQLite; images are injected into chat payloads as data URLs.
- **RAG Storage**: `rag_documents`, `rag_chunks`, `rag_chunks_fts`, and `rag_embeddings` live in SQLite.
- **Settings**: Stored in SQLite; API keys also load from `API_KEY.txt` or environment variables.
- **Store**: LangGraph uses an in-memory store in `core/store` for reflections (non-persistent).

### Testing Strategy
- **Unit Tests**: pytest for core logic, persistence, RAG, providers, and viewmodels.
- **Async Testing**: pytest-asyncio with `asyncio_mode=auto`.

### Git Workflow
- Feature branches and PRs (per README contributing notes).
- Semantic versioning.

## Domain Context
- **Workspaces and Sessions**: Workspaces contain sessions, sessions contain messages and artifact collections.
- **Artifacts**: Text or code; multi-artifact tabs in the UI (+ Art / + Code) with version navigation and export on app close.
- **RAG**: PDF imports and (optional) text artifacts are indexed for local retrieval; context is injected into reply/generate/rewrite nodes.
- **Deep Search**: UI toggle and settings exist for Exa/Firecrawl; graph-level web search is currently a placeholder.
- **Routing**: The graph routes based on explicit state flags (highlighted text/code, quick actions) and LLM-based intent decisions.
- **Streaming**: OpenRouter streaming drives responsive updates in the UI.
- **Defaults**: Default model is `anthropic/claude-3.5-sonnet`, configurable in settings.

## Important Constraints
- **Qt Threading**: Graph execution and PDF conversion run off the main UI thread (QThread) to avoid freezes.
- **Configuration**: `OPENROUTER_API_KEY` is required; optional keys enable LangSmith, Exa, and Firecrawl.
- **Image Attachments**: Screen captures are saved to `/home/m/Documents/Attractor_Imagens`; images attach only if the model supports vision.
- **Incomplete Nodes**: Summarizer/title/web search nodes exist but are placeholders in the current graph.

## External Dependencies
- **OpenRouter API**: Required LLM backend.
- **LangSmith**: Optional tracing.
- **Exa + Firecrawl**: Optional deep search and scraping.
- **Docling**: Optional PDF to Markdown conversion.
