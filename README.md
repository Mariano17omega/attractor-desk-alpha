# Open Canvas Python

A Python port of [Open Canvas](https://github.com/langchain-ai/open-canvas) - an AI-powered writing and coding assistant with artifact management.

## Features

- **Chat Interface**: Interact with AI to generate and modify content
- **Artifact Management**: Create and manage text and code artifacts with version history
- **Multiple LLM Support**: Uses OpenRouter for unified access to multiple AI models
- **Memory/Reflections**: Persistent user preferences and style guidelines
- **Web Search** (Optional): Search the web for additional context via Exa
- **Desktop Application**: Native PySide6 UI

## Architecture

```
open-canvas-py/
├── core/           # Reusable backend (no UI dependencies)
│   ├── graphs/     # LangGraph graph definitions
│   ├── llm/        # OpenRouter LLM wrapper
│   ├── providers/  # External service integrations
│   ├── store/      # In-memory data store
│   └── utils/      # Utility functions
├── ui/             # PySide6 desktop application
└── API_KEY.txt     # API key configuration
```

## Installation

### Prerequisites

- Python 3.11+
- OpenRouter API key

### Setup

1. Clone the repository:
   ```bash
   cd open-canvas-py
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # or
   .venv\Scripts\activate     # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure API keys:
   ```bash
   cp API_KEY.txt.example API_KEY.txt
   # Edit API_KEY.txt with your keys
   ```

## Configuration

Edit `API_KEY.txt` with your API keys:

```
# Required
OPENROUTER_API_KEY=sk-or-...

# Optional - LangSmith tracing
LANGSMITH_API_KEY=ls-...

# Optional - Web search
EXA_API_KEY=...

# Optional - Web scraping
FIRECRAWL_API_KEY=...
```

## Usage

### Run the Desktop Application

```bash
python -m ui.main
```

### Use the Core Library

```python
from core.graphs.open_canvas import graph
from langchain_core.messages import HumanMessage

# Run the graph
result = await graph.ainvoke({
    "messages": [HumanMessage(content="Write me a poem about Python")]
})

print(result["artifact"])
```

## Development

### Run Tests

```bash
pytest
```

### Code Formatting

```bash
black .
ruff check .
```

## License

MIT License - see the original [Open Canvas](https://github.com/langchain-ai/open-canvas) project for details.

## Acknowledgments

This project is a Python port of [Open Canvas](https://github.com/langchain-ai/open-canvas) by LangChain, Inc.
