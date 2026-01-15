<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->
 
# Project Context

## Purpose
Attractor Desk is a native Python desktop application for AI-assisted writing and coding.  
It evolves the original Open Canvas concept into a **local-first, desktop experience** where users collaborate with an AI to create and iteratively refine *artifacts* side-by-side with a chat interface.

The application emphasizes:
- Persistent workspaces
- Artifact versioning
- Optional local RAG for context grounding
- Agentic workflows using LangGraph

The primary use case is **academic research** (master’s and PhD level), including analysis, summarization, and iterative refinement of technical texts and code.

## Tech Stack
- **Languages**: Python 3.11+
- **Packaging**: `pyproject.toml` with setuptools  
  CLI entrypoint: `attractor-desk` → `ui.main:main`
- **UI Framework**: PySide6 (Qt for Python), QSS theming in `ui/styles.py`
- **Agent / LLM Orchestration**: LangGraph + LangChain  
  LangSmith tracing is optional
- **LLM Provider**: OpenRouter via a custom `OpenRouterChat` wrapper (httpx, streaming, tool calls)
- **Embeddings**: OpenRouter embeddings (`openai/text-embedding-3-small` default)
- **RAG**: SQLite FTS5 + in-process cosine similarity + RRF fusion; optional LLM rerank
- **Search / Scraping**: Exa search + Firecrawl scraping (optional extras)
- **PDF Ingestion**: Docling (optional extra for PDF → Markdown)
- **Screen Capture**: `mss` for full-screen / region capture
- **Persistence**: SQLite via `core/persistence` (WAL) and JSON-serialized artifacts
- **Testing**: pytest, pytest-asyncio
- **Utilities**: Pydantic (LLM and artifact types), dataclasses for persisted domain models

## Project Conventions

### Code Style
- **Formatter**: Black (line length 100)
- **Linter**: Ruff (select E/F/I/W, ignore E501)
- **Type Checking**: Mypy (`warn_return_any`, `warn_unused_ignores`, `ignore_missing_imports`)
- **Naming**:
  - `snake_case` for functions and variables
  - `PascalCase` for classes

### Architecture Patterns
- **MVVM (Model–View–ViewModel)**  
  UI logic in `ui/viewmodels` emits Qt signals to widgets in `ui/widgets`.
- **Core / UI Separation**
  - `core/`: Business logic, graph orchestration, providers, persistence, and domain types  
    (no UI dependencies)
  - `ui/`: PySide6 UI, viewmodels, and widgets
- **LangGraph Graphs**
  - Main graph: `core/graphs/open_canvas/graph.py`
  - Nodes: `core/graphs/open_canvas/nodes`
  - RAG subgraph: `core/graphs/rag/graph.py`
- **Repositories**
  - SQLite repositories in `core/persistence` wrap DB access
- **Services**
  - PDF conversion and artifact export in `core/services`
- **Threading**
  - Graph execution, PDF conversion, and RAG indexing run in `QThread` workers to keep UI responsive
- **Settings**
  - `SettingsViewModel` owns user-configurable options and persists via `SettingsRepository`

### Data and Persistence
- **SQLite**
  - Default DB: `~/.open_canvas/database.db` (WAL)
  - Tables: workspaces, sessions, messages, message_attachments, artifacts, RAG, settings
- **Artifacts**
  - Stored as `ArtifactCollectionV1` JSON
  - Versioned `ArtifactV3` contents with export metadata
- **Export**
  - Artifacts export to `~/Documents/Artifacts/Articles`
- **Attachments**
  - Message attachments store file paths in SQLite
  - Images injected into chat payloads as data URLs
- **RAG Storage**
  - `rag_documents`, `rag_chunks`, `rag_chunks_fts`, `rag_embeddings`
- **Settings**
  - Stored in SQLite
  - API keys stored securely in OS keyring (Keychain/Secret Service/Credential Locker)
  - Fallback to environment variables for CI/CD
  - Legacy `API_KEY.txt` supported with migration prompt
- **Store**
  - LangGraph uses an in-memory store in `core/store` for reflections (non-persistent)

### Testing Strategy
- **Unit Tests**
  - pytest for core logic, persistence, RAG, providers, and viewmodels
- **Async Testing**
  - pytest-asyncio with `asyncio_mode=auto`

### Git Workflow
- Feature branches and PRs
- Semantic versioning

## Domain Context
- **Workspaces / Sessions**
  - Workspaces contain sessions
  - Sessions contain messages and artifact collections
- **Artifacts**
  - Text or code
  - Multi-artifact tabs in the UI (+ Art / + Code)
  - Version navigation and export on app close
- **RAG**
  - PDF imports and (optional) text artifacts are indexed for local retrieval
  - Context injected into reply / generate / rewrite nodes
- **Deep Search**
  - UI toggle and settings exist for Exa / Firecrawl
  - Graph-level web search nodes currently exist as placeholders
- **Routing**
  - Graph routes based on explicit state flags and LLM-based intent decisions
- **Streaming**
  - OpenRouter streaming drives responsive UI updates
- **Defaults**
  - Default model: `anthropic/claude-3.5-sonnet` (configurable)

## Important Constraints
- **Qt Threading**
  - Graph execution and PDF conversion must not block the UI thread
- **Configuration**
  - `OPENROUTER_API_KEY` is required (stored in OS keyring or environment variable)
  - Optional keys enable LangSmith, Exa, and Firecrawl
- **Image Attachments**
  - Screen captures saved to `/home/m/Documents/Attractor_Imagens`
  - Images attach only if the selected model supports vision
- **Incomplete Nodes**
  - Summarizer, title, and web search nodes exist but may be placeholders

## External Dependencies
- OpenRouter API (required)
- LangSmith (optional)
- Exa + Firecrawl (optional)
- Docling (optional)

