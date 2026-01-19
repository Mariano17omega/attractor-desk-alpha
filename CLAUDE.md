# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Attractor Desk** (v0.3.0 Alpha) is a native Python desktop application for AI-assisted coding and writing. It evolved from the Open Canvas concept, combining a LangGraph-based cognitive engine with a PySide6 (Qt) desktop UI. Users collaborate with AI to create and iteratively refine "artifacts" (code or text documents) alongside a chat interface.

**Primary use case**: Academic research (master's/PhD level) including analysis, summarization, and iterative refinement of technical texts and code.

**Tech Stack**: Python 3.11+, PySide6 (Qt), LangGraph + LangChain, OpenRouter (multi-LLM support), SQLite (persistence + RAG), optional Exa/Firecrawl (web search), Docling (PDF ingestion), mss (screen capture).

## Development Commands

### Installation & Setup

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install in editable mode
pip install -e .

# Install with optional dependencies
pip install -e ".[dev]"       # Development tools
pip install -e ".[search]"    # Exa + Firecrawl web search
pip install -e ".[pdf]"       # Docling PDF support
```

### Running the Application

```bash
# Primary entrypoint
attractor-desk

# Alternative
python -m ui.main
```

### Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_rag_pipeline.py

# Run specific test function
pytest tests/test_rag_pipeline.py::test_global_rag_index_worker_success

# Run with verbose output
pytest -v

# Run tests matching pattern
pytest -k "rag"
```

### Code Quality

```bash
# Format code (line length 100)
black .

# Lint
ruff check .

# Type check
mypy core/ ui/
```

### Database Management

```bash
# Clear memory (deletes SQLite database)
rm -f ~/.attractor_desk/database.db*
```

## Architecture

### Core / UI Separation

**Strict separation of concerns:**
- **`core/`**: UI-agnostic business logic, graph orchestration, providers, persistence, domain types (no PySide6 dependencies)
- **`ui/`**: PySide6 UI, MVVM pattern (viewmodels + widgets)

### MVVM Pattern

UI follows Model-View-ViewModel:
- **ViewModels** (`ui/viewmodels/`): Emit Qt signals, own business state
- **Widgets** (`ui/widgets/`): Qt UI components, react to signals
- **Models**: Domain types in `core/types.py`, persistence in `core/persistence/`

### LangGraph Architecture

**Main Graph** (`core/graphs/open_canvas/graph.py`):
1. **Routing Phase**: `generatePath` determines action from user input
2. **Contextualization Phase**: RAG retrieval (`rag_graph` subgraph) and web search
3. **Artifact Operations Phase**: `ArtifactOps` subgraph handles all artifact mutations (generate, rewrite, update)
4. **Housekeeping Phase**: Reflection, state cleanup, title generation, summarization

**RAG Subgraph** (`core/graphs/rag/graph.py`):
- Decides whether to retrieve → Selects scope (global/local) → Rewrites query → Retrieves
- **Global RAG**: Searches across all indexed artifacts
- **Local RAG**: Scoped to a specific PDF document (`conversation_mode == "chatpdf"`)

**Graph Nodes**:
- Most nodes in `core/graphs/open_canvas/nodes/` as standalone modules
- Some lightweight nodes (`webSearch`, `summarizer`, `generateTitle`) defined directly in `graph.py`
- Each node is a function taking `OpenCanvasState` and returning state updates
- Key nodes: `generate_path`, `reply_to_general_input`, artifact ops (generate/rewrite/update), `reflect`, `image_processing`

**State** (`core/graphs/open_canvas/state.py`):
- `OpenCanvasState` (Pydantic model) tracks conversation, artifacts, routing flags
- Key routing fields: `next`, `artifact_action`, `artifact_action_params`, `rag_should_retrieve`

### Persistence Layer

**SQLite** (`core/persistence/database.py`):
- Default DB: `~/.attractor_desk/database.db` (WAL mode)
- Tables: workspaces, sessions, messages, message_attachments, artifacts, RAG (documents, chunks, FTS5, embeddings), settings

**Repositories** (`core/persistence/`):
- `WorkspaceRepository`, `SessionRepository`, `MessageRepository`, `ArtifactRepository`, `RAGRepository`, `SettingsRepository`
- Each repository wraps database access for a specific domain

**Artifacts**:
- Stored as `ArtifactCollectionV1` JSON in database
- Versioned `ArtifactV3` contents with export metadata (text/code artifacts)
- `ArtifactPdfV1` for PDF artifacts in ChatPDF mode
- Export path: `~/Documents/Artifacts/Articles` (via `ArtifactExportService`)
- Markdown content is rendered in message bubbles

**API Keys**:
- OpenRouter, Exa, Firecrawl: Stored securely in OS keyring (Keychain/Secret Service/Credential Locker) via `KeyringService`
- LangSmith: Dev-only, intentionally NOT stored in keyring (read from environment variable or `API_KEY.txt`)
- Fallback to environment variables (`OPENROUTER_API_KEY`, `EXA_API_KEY`, `FIRECRAWL_API_KEY`, `LANGSMITH_API_KEY`)
- Legacy `API_KEY.txt` supported with auto-migration to keyring

### RAG System

**Architecture**:
- SQLite FTS5 (full-text search) + cosine similarity (in-process embeddings) + RRF fusion
- Optional LLM rerank for top results
- Embeddings via OpenRouter (`openai/text-embedding-3-small` default)

**Modes**:
- **Global RAG**: Available in all sessions except ChatPDF; indexes text artifacts and manually imported documents from configurable folder path
- **ChatPDF RAG**: Isolated, per-PDF RAG scope active only in ChatPDF sessions; never combined with Global RAG

**Indexing**:
- PDF conversion uses Docling (Markdown output) via `DoclingService`
- Text artifacts optionally indexed
- Background workers in `QThread` (in `ChatViewModel`) for indexing (non-blocking UI)
- Services: `GlobalRAGService`, `LocalRAGService`, `RAGService` for orchestration

**Tables**:
- `rag_documents`: Document metadata
- `rag_chunks`: Chunked text
- `rag_chunks_fts`: FTS5 index
- `rag_embeddings`: Vector embeddings
- Each ChatPDF session gets its own isolated RAG scope

### Threading Model

**UI Thread Safety**:
- Graph execution runs in `QThread` workers (defined in `ui/viewmodels/chat_viewmodel.py`)
- PDF conversion runs in background threads
- RAG indexing runs in background threads
- Never block UI thread with long-running operations

### OpenRouter Integration

**Custom Wrapper** (`core/llm/openrouter_chat.py`):
- Built on httpx (streaming, tool calls)
- Supports vision models (image attachments as data URLs)
- Default model: `anthropic/claude-3.5-sonnet` (configurable in settings)
- Separate configurable `image_model` for multimodal processing (screenshots, image attachments)
- Model capabilities tracked via `ModelCapabilitiesService`

### Settings Management

**SettingsCoordinator** (`ui/viewmodels/settings/coordinator.py`):
- Refactored from 1148-line God Object into focused subsystems
- User-configurable options: models, temperature, max tokens, API keys
- Persisted via `SettingsRepository` to SQLite
- API keys stored in OS keyring
- See /Documentation/VIEWMODEL_REFACTORING_PLAN.md for architecture details

### Chat/ViewModel Architecture

**ChatViewModel** (`ui/viewmodels/chat_viewmodel.py`):
- **Thin compatibility wrapper** (64 lines) extending ChatCoordinator
- Maintains backward compatibility with existing UI code
- **DO NOT add new logic to ChatViewModel** - extend subsystems instead

**ChatCoordinator** (`ui/viewmodels/chat/coordinator.py`):
- **Main orchestration facade** (358 lines) coordinating all chat subsystems
- Forwards signals from all subsystems to maintain API compatibility
- Manages subsystem lifecycle and cross-cutting concerns

**Chat Subsystems** (`ui/viewmodels/chat/`):

1. **SessionManager** (126 lines)
   - Session lifecycle (load, clear, switch)
   - Message loading and LangChain format conversion
   - Session state management

2. **GraphExecutionHandler** (409 lines)
   - LangGraph execution orchestration
   - Message sending and result processing
   - GraphWorker lifecycle management
   - Loading state and cancellation

3. **GraphWorker** (69 lines)
   - QThread for async graph execution
   - Proper database connection cleanup
   - Signal-based result delivery

4. **ChatPdfService** (198 lines)
   - ChatPDF mode initialization
   - Isolated RAG scope management
   - PDF artifact creation

5. **PdfHandler** (158 lines)
   - PDF conversion via Docling
   - PDF import to text artifacts
   - RAG indexing coordination

6. **ArtifactViewModel** (154 lines)
   - Artifact state and versioning
   - Artifact navigation (prev/next)
   - Conversation mode tracking

7. **RagOrchestrator** (131 lines)
   - RAG indexing coordination
   - Background worker management
   - Global/local RAG scope handling

8. **AttachmentHandler** (85 lines)
   - Image attachment management
   - Multimodal input preparation

**Architecture Rules for Future Work**:
- ✅ Add new features to appropriate subsystem or create new subsystem
- ✅ ChatCoordinator handles orchestration and signal forwarding only
- ❌ DO NOT add business logic to ChatViewModel (it's just a wrapper)
- ❌ DO NOT add business logic to ChatCoordinator (delegate to subsystems)
- ✅ Each subsystem should have a single, clear responsibility
- ✅ Use dependency injection for subsystem communication
- ✅ Signals flow: Subsystem → ChatCoordinator → UI

**Documentation**:
- Documentation/CHATVIEWMODEL_REFACTORING_PLAN.md (full architecture details)
- Documentation/VIEWMODEL_REFACTORING_PLAN.md (full architecture details)
- Documentation/PHASE1_COMPLETION_SUMMARY.md (AttachmentHandler, ArtifactViewModel)
- Documentation/PHASE2_COMPLETION_SUMMARY.md (RagOrchestrator, PdfHandler)
- Documentation/PHASE3_COMPLETION_SUMMARY.md (ChatPdfService, GraphExecutionHandler, SessionManager)
- Documentation/PHASE4_COMPLETION_SUMMARY.md (ChatCoordinator, final integration)


## Code Style & Conventions

- **Formatter**: Black (line length 100)
- **Linter**: Ruff (select E/F/I/W, ignore E501)
- **Type Checking**: Mypy (`warn_return_any`, `warn_unused_ignores`, `ignore_missing_imports`)
- **Naming**: `snake_case` functions/variables, `PascalCase` classes
- **Testing**: pytest + pytest-asyncio (`asyncio_mode=auto`)

## Domain Model

**Workspaces → Sessions → Messages + Artifacts**:
- Workspaces contain sessions
- Sessions contain messages and artifact collections
- Each session can have multiple artifacts (tabs in UI: "+ Art", "+ Code")

**Artifacts**:
- Type: `text`, `code`, or `pdf` (`ArtifactPdfV1` for ChatPDF mode)
- Version navigation and export on app close
- Multi-artifact tabs in UI
- Markdown content rendered in message bubbles

**Conversation Modes**:
- **Normal**: Standard chat with optional Global RAG
- **ChatPDF**: Dedicated PDF interaction mode with:
  - Native PySide6 `PdfViewerWidget` for in-app PDF rendering
  - Isolated RAG scope per uploaded PDF (separate from Global RAG)
  - PDF content parsed via Docling, chunked, and embedded
  - Questions answered exclusively from the uploaded PDF content

**Deep Search**:
- UI toggle and settings for Exa/Firecrawl
- `web_search_node` dynamically classifies queries, generates search terms, and injects results

**Image Processing**:
- `imageProcessing` node handles image attachments for multimodal models
- Screenshots captured via `mss` and saved locally
- Separate `image_model` configuration for vision capabilities

## Configuration

**Required**:
- `OPENROUTER_API_KEY`: Set via Settings UI or environment variable

**Optional**:
- `LANGSMITH_API_KEY`: LangSmith tracing (dev-only, not stored in keyring)
- `EXA_API_KEY`: Exa web search (stored in keyring)
- `FIRECRAWL_API_KEY`: Firecrawl scraping (stored in keyring)

**Image Attachments**:
- Screen captures saved to `~/Documents/Attractor_Imagens` (configurable)
- Only attached if selected `image_model` supports vision

## Important Constraints

- **Qt Threading**: Never run graph execution, PDF conversion, or RAG indexing on UI thread
- **Database**: Path: `~/.attractor_desk/database.db` (WAL mode)
- **LangGraph Store**: In-memory only (reflections, non-persistent)
- **RAG Isolation**: Global RAG and ChatPDF RAG are completely isolated; never combined
