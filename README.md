# Attractor Desk

![Status: Alpha](https://img.shields.io/badge/Status-Alpha-orange.svg)

**Attractor Desk** is a native Python desktop application that redefines AI-assisted coding and writing. Evolved from the [Open Canvas](https://github.com/langchain-ai/open-canvas) concept, it combines a powerful cognitive engine with a seamless user interface to manage "artifacts"—structured content that you iterate on collaboratively with AI.

## Features

- **🧠 Cognitive Engine**: Built on LangGraph, the agent understands context, manages state, and reasons about your tasks.
- **📄 Artifact Management**: Treat code and text as first-class citizens. Version control, diff viewing, and targeted updates are built-in.
- **🖥️ Native Desktop Experience**: precise control and high performance using PySide6 (Qt).
- **🔌 Multi-LLM Support**: Connect to Claude, GPT-4, Llama 3, and more via OpenRouter.
- **💾 Persistent Memory**: The system remembers your style guidelines and key project details across sessions.
- **🌐 Deep Search**: Integrated Agentic web search (via Exa) for fact-checking and research.

## Architecture

Want to understand how it works under the hood? Check out our detailed **[Architecture Documentation](ARCHITECTURE.md)**.

We follow a strict separation of concerns:
- **Core**: UI-agnostic business logic and state management.
- **UI**: MVVM-based presentation layer using Qt.

## Installation

### Prerequisites

- Python 3.11 or higher
- An [OpenRouter](https://openrouter.ai/) API key

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/attractor-desk.git
   cd attractor-desk
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # or
   .venv\Scripts\activate     # Windows
   ```

3. **Install in editable mode:**
   ```bash
   pip install -e .
   ```

4. **Configure your API keys:**
   ```bash
   cp API_KEY.txt.example API_KEY.txt
   ```
   Edit `API_KEY.txt` and add your `OPENROUTER_API_KEY`.

## Usage

### Running the Application

Once installed, you can start the application from anywhere in your virtual environment:

```bash
attractor-desk
```

Alternatively, you can run it as a module:

```bash
python -m ui.main
```

### Key Configuration

Manage your settings in `API_KEY.txt`:

```ini
# Required
OPENROUTER_API_KEY=sk-or-...

# Optional: Enable deep search
EXA_API_KEY=...

# Optional: Enable LangSmith tracing
LANGSMITH_API_KEY=ls-...
```

## contributing

We welcome contributions! Please see the `core/` directory for backend logic and `ui/` for frontend components.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the `pyproject.toml` file for details.

## Acknowledgments

This project is a Python port and evolution of [Open Canvas](https://github.com/langchain-ai/open-canvas) by LangChain, Inc.
