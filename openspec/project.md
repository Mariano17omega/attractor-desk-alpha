# Project Context

## Purpose
Open Canvas is a native Python desktop application that serves as an AI-powered writing and coding assistant. It is a port of the original [Open Canvas](https://github.com/langchain-ai/open-canvas) project, designed to provide a collaborative interface where users can interact with an AI to generate and modify content ("artifacts") side-by-side with a chat interface. The goal is to offer a seamless, local-first experience for iterative content creation using state-of-the-art LLMs via OpenRouter.

## Tech Stack
- **Languages**: Python 3.11+
- **Frontend Framework**: PySide6 (Qt for Python)
- **AI/LLM Orchestration**: LangGraph, LangChain, LangSmith (tracing)
- **LLM Provider**: OpenRouter (Unified API for various models like Claude 3.5 Sonnet)
- **Web Search/Scraping**: Exa (Search), Firecrawl (Scraping)
- **Testing**: Pytest, Pytest-Asyncio
- **Utilities**: Pydantic (Data validation), Httpx (Async HTTP)

## Project Conventions

### Code Style
- **Formatter**: Black (line length 100)
- **Linter**: Ruff
- **Type Checking**: Mypy (strict type hinting required)
- **Naming**: Snake_case for functions/variables, PascalCase for classes (standard Python).

### Architecture Patterns
- **MVVM (Model-View-ViewModel)**: The UI logic is separated from the view using ViewModels (e.g., `ChatViewModel`) that emit signals to Views (`ChatPanel`, `ArtifactPanel`).
- **Core/UI Separation**:
    - `core/`: Contains pure business logic, LangGraph definitions, and LLM integrations. No UI dependencies allowed.
    - `ui/`: Contains all PySide6 widgets, windows, and viewmodels.
- **Dependency Injection**: Services and configuration are passed down to ViewModels.

### Testing Strategy
- **Unit Tests**: `pytest` for testing core logic and view models.
- **Async Testing**: Extensive use of `pytest-asyncio` for ensuring async LangGraph flows work correctly.

### Git Workflow
- Feature branches merged into main.
- Semantic versioning.

## Domain Context
- **Artifacts**: Distinct logic/content blocks (e.g., specific code files, markdown documents) that the AI generates. These are separate from the ephemeral chat and are displayed in a dedicated panel.
- **Streaming**: The application heavily relies on streaming LLM tokens to provide a responsive UI.
- **LangGraph**: The backend logic is a graph, not a linear chain, allowing for complex routing (e.g., deciding whether to reply or update an artifact).

## Important Constraints
- **Qt Threading**: Long-running (AI) tasks must run off the main UI thread to prevent freezing.
- **Configuration**: API keys are loaded from `API_KEY.txt` (not git-tracked) or environment variables.

## External Dependencies
- **OpenRouter API**: Primary source for LLM intelligence.
- **LangSmith**: Optional tracing for debugging AI logic.
- **Exa/Firecrawl**: Optional tools for web capabilities.
