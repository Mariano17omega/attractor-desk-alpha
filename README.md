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

   **Option A: Via Settings (Recommended)**
   
   Launch the application and configure your API keys in **Settings** → **Model Configuration**. Keys are stored securely in your operating system's credential vault (Keychain on macOS, Secret Service on Linux, Credential Locker on Windows).

   **Option B: Environment Variables**
   
   For CI/CD or containerized environments:
   ```bash
   export OPENROUTER_API_KEY=sk-or-...
   export EXA_API_KEY=...  # Optional
   ```

   **Option C: Legacy File (Deprecated)**
   
   For backwards compatibility, copy `API_KEY.txt.example` to `API_KEY.txt`. On first launch, keys will be migrated to secure storage.
   ```bash
   cp API_KEY.txt.example API_KEY.txt
   # Edit API_KEY.txt and add your keys
   ```

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

### API Key Configuration

API keys are stored securely in your operating system's credential vault:

| Platform | Backend |
|----------|-------------------|
| macOS | Keychain |
| Linux | Secret Service (GNOME Keyring, KWallet) |
| Windows | Credential Locker |

**Configure via Settings UI:**
1. Launch Attractor Desk
2. Open Settings (Ctrl+,)
3. Navigate to Model Configuration
4. Enter your OpenRouter API key
5. (Optional) Configure Exa, FireCrawl, or LangSmith keys

**Environment Variable Fallback:**

For CI/CD pipelines or headless environments, set environment variables:
```bash
export OPENROUTER_API_KEY=sk-or-...
export EXA_API_KEY=...           # Optional: Deep search
export FIRECRAWL_API_KEY=...     # Optional: Web scraping
export LANGSMITH_API_KEY=ls-...  # Optional: Tracing
```

### Migrating from API_KEY.txt

If you have an existing `API_KEY.txt` file:
1. Launch the application
2. Keys are automatically migrated to secure storage
3. You may safely delete `API_KEY.txt` after confirming the app works

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
