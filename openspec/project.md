# Project Context

## Purpose
Attractor Desk is a native Python desktop application for AI-assisted writing and coding. It evolves the original [Open Canvas](https://github.com/langchain-ai/open-canvas) concept into a local-first, desktop experience where users collaborate with an AI to create and iteratively refine "artifacts" side-by-side with a chat interface.

## Tech Stack
- **Languages**: Python 3.11+
- **UI Framework**: PySide6 (Qt for Python)
- **Agent/LLM Orchestration**: LangGraph + LangChain; LangSmith tracing is optional
- **LLM Provider**: OpenRouter via a custom `OpenRouterChat` wrapper (httpx, streaming, tool calls)
- **Search/Scraping**: Exa search + Firecrawl scraping (optional extras)
- **PDF Ingestion**: Docling (optional extra for PDF to Markdown)
- **Persistence**: SQLite via `core/persistence` and JSON-serialized artifacts
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
- **LangGraph Graph**: `core/graphs/open_canvas/graph.py` wires node modules in `core/graphs/open_canvas/nodes`.
- **Repositories**: SQLite repositories in `core/persistence` wrap DB access.
- **Services**: PDF conversion and artifact export live in `core/services`.

### Data and Persistence
- **SQLite**: Default DB at `~/.open_canvas/database.db` with tables for workspaces, sessions, messages, artifacts, and settings.
- **Artifacts**: Stored as `ArtifactCollectionV1` JSON with versioned `ArtifactV3` contents and export metadata.
- **Export**: Artifacts export to `~/Documents/Artifacts/Articles` via `ArtifactExportService`.
- **Settings**: Stored in SQLite; API keys also load from `API_KEY.txt` or environment variables.
- **Store**: LangGraph uses an in-memory store in `core/store`.

### Testing Strategy
- **Unit Tests**: pytest for core logic, persistence, and viewmodels.
- **Async Testing**: pytest-asyncio with `asyncio_mode=auto`.

### Git Workflow
- Feature branches and PRs (per README contributing notes).
- Semantic versioning.

## Domain Context
- **Workspaces and Sessions**: Workspaces contain sessions, sessions contain messages and artifact collections.
- **Artifacts**: Text or code; multi-artifact tabs in the UI (+ Art / + Code) with version navigation.
- **Routing**: The graph routes based on explicit state flags (highlighted text/code, quick actions) and LLM-based intent decisions.
- **Streaming**: OpenRouter streaming drives responsive updates in the UI.
- **Defaults**: Default model is `anthropic/claude-3.5-sonnet`, configurable in settings.

## Important Constraints
- **Qt Threading**: Graph execution and PDF conversion run off the main UI thread (QThread) to avoid freezes.
- **Configuration**: `OPENROUTER_API_KEY` is required; optional keys enable LangSmith, Exa, and Firecrawl.
- **Incomplete Nodes**: Summarizer/title/web search nodes exist but are placeholders in the current graph.

## External Dependencies
- **OpenRouter API**: Required LLM backend.
- **LangSmith**: Optional tracing.
- **Exa + Firecrawl**: Optional deep search and scraping.
- **Docling**: Optional PDF to Markdown conversion.
