# Open Canvas Migration Notes

This document describes the architectural decisions, assumptions, and differences between the original TypeScript implementation and this Python port.

## Overview

This Python port of Open Canvas migrates the core agent system from TypeScript/LangGraph to Python while:
- Preserving the complete graph architecture
- Maintaining verbatim prompts
- Using OpenRouter as the unified LLM provider
- Replacing the Next.js frontend with a PySide6 desktop application

## Architectural Decisions

### 1. LLM Provider: OpenRouter Only

**Original**: Multiple provider SDKs (OpenAI, Anthropic, Fireworks, Google GenAI, etc.)

**Python Port**: Single OpenRouter wrapper

**Rationale**:
- Simplifies code by using one API endpoint
- Reduces dependency count
- OpenRouter provides access to all the same models
- Unified error handling and streaming

**Impact**:
- Model names use OpenRouter format: `anthropic/claude-3.5-sonnet` instead of `claude-3-5-sonnet-latest`
- Provider-specific features (like Anthropic's native PDF support) may require workarounds

### 2. No HTTP/WebSocket IPC

**Original**: Frontend communicates with agents via HTTP API (LangGraph CLI/Server)

**Python Port**: Direct Python function calls

**Rationale**:
- Desktop application doesn't need network overhead
- Simpler debugging and error handling
- No port conflicts or networking issues

**Impact**:
- Reflection scheduling uses in-process delays instead of background runs
- Thread management is simplified for desktop use case

### 3. In-Memory Store

**Original**: LangGraph's built-in store with persistence

**Python Port**: Simple in-memory dictionary store

**Rationale**:
- Desktop apps typically don't need cross-session persistence
- Simpler implementation for initial version

**Impact**:
- Reflections/memories are lost between sessions
- Future enhancement: Add SQLite or file-based persistence

### 4. State Management

**Original**: TypeScript Annotations with custom reducers

**Python Port**: Pydantic models with `Annotated` types

**Differences**:
```python
# Original TS
export const OpenCanvasGraphAnnotation = Annotation.Root({
  ...MessagesAnnotation.spec,
  _messages: Annotation<BaseMessage[], Messages>({
    reducer: (state, update) => {...}
  }),
});

# Python port uses Pydantic
class OpenCanvasState(BaseModel):
    messages: Annotated[list[BaseMessage], add_messages] = Field(...)
    _messages: Annotated[list[BaseMessage], internal_messages_reducer] = Field(...)
```

### 5. Streaming

**Original**: Uses LangGraph streaming callbacks

**Python Port**: Thread-based async with Qt signals

**Implementation**:
- Graph runs in a QThread to avoid blocking UI
- Results are emitted via Qt signals to update UI
- Full streaming (token-by-token) is available via the OpenRouter wrapper

## Preserved Elements

### Prompts

All prompts are copied **verbatim** from the TypeScript source:
- `prompts.py` contains exact copies of all prompt templates
- Placeholder syntax (`{variable}`) is maintained
- XML tags are preserved exactly

### Graph Structure

The graph topology is identical:
- Same nodes (generatePath, generateArtifact, rewriteArtifact, etc.)
- Same edges and conditional routing
- Same state flow

### Node Logic

Each node implements the same logic:
- Same input validation
- Same prompt construction
- Same output formatting

## Known Differences

### 1. Reflection Scheduling

**Original**: Uses LangGraph background runs with `afterSeconds` delay

**Python Port**: Reflection runs immediately (no debouncing)

**Reason**: Background scheduling requires LangGraph server infrastructure

**Future**: Could implement using Python's `asyncio` with debounce logic

### 2. Thread/Run Management

**Original**: Full thread history and run management via LangGraph SDK

**Python Port**: Simplified single-thread model

**Reason**: Desktop app typically handles one conversation at a time

### 3. Context Documents

**Original**: Full multi-format document handling with provider-specific formatting

**Python Port**: Simplified text extraction

**Impact**: PDF and complex document handling may need enhancement

### 4. Summarizer Graph

**Original**: Full implementation with thread state update

**Python Port**: Placeholder implementation

**Reason**: Requires LangGraph thread state management not available in desktop mode

### 5. Web Search

**Original**: Uses `@langchain/exa` package

**Python Port**: Uses `exa-py` package with similar interface

**Status**: Fully functional if EXA_API_KEY is configured

## Optional Features

These features are implemented but require API keys:

| Feature | API Key | Package |
|---------|---------|---------|
| LangSmith Tracing | `LANGSMITH_API_KEY` | built-in |
| Exa Web Search | `EXA_API_KEY` | `exa-py` |
| FireCrawl Scraping | `FIRECRAWL_API_KEY` | `firecrawl-py` |

All optional features fail gracefully if not configured.

## Testing Recommendations

### Core Testing (No UI)

```python
from core.graphs.open_canvas import graph
from langchain_core.messages import HumanMessage

result = await graph.ainvoke({
    "messages": [HumanMessage(content="Write a haiku about Python")]
})

assert result["artifact"] is not None
assert result["artifact"].contents[0].type in ["text", "code"]
```

### UI Testing

1. Launch: `python -m ui.main`
2. Type a message requesting artifact generation
3. Verify artifact appears in right panel
4. Request modification and verify version history

## Future Enhancements

1. **Persistent Storage**: Add SQLite backend for memory/reflections
2. **Full Streaming**: Token-by-token streaming in chat UI
3. **Document Upload**: Support PDF and file uploads
4. **Custom Actions**: UI for creating/managing quick actions
5. **Settings Panel**: Model selection, temperature adjustment
6. **Theme Support**: Dark/light mode toggle

## File Mapping Reference

| TypeScript File | Python File |
|-----------------|-------------|
| `apps/agents/src/open-canvas/index.ts` | `core/graphs/open_canvas/graph.py` |
| `apps/agents/src/open-canvas/state.ts` | `core/graphs/open_canvas/state.py` |
| `apps/agents/src/open-canvas/prompts.ts` | `core/graphs/open_canvas/prompts.py` |
| `apps/agents/src/open-canvas/nodes/*.ts` | `core/graphs/open_canvas/nodes/*.py` |
| `apps/agents/src/utils.ts` | `core/utils/*.py` |
| `packages/shared/src/types.ts` | `core/types.py` |
| `packages/shared/src/constants.ts` | `core/constants.py` |

## Version History

- **v0.1.0** (Initial): Core graph implementation, basic UI
