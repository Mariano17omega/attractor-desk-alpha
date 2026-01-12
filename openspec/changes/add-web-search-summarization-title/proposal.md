# Change: Implement web search, summarization, and session title generation

## Why
The Open Canvas-based graph currently contains placeholder nodes for web search, summarization, and title generation. These gaps prevent deep search and long-context behavior from working as intended and limit session metadata quality.

## What Changes
- Implement a web search flow that classifies user messages, generates search queries, and injects results into model context.
- Implement conversation summarization when internal message size exceeds the character budget.
- Generate concise session titles after the first exchange using conversation and artifact context.
- Integrate deep-search toggles and settings into the graph input and internal message handling.

## Impact
- Affected specs: manage-chat-sessions (modified), web-search (new), conversation-summarization (new)
- Affected code: core/graphs/open_canvas, core/graphs/web_search (new), core/graphs/summarizer (new), core/graphs/thread_title (new), ui/viewmodels/chat_viewmodel.py, core/utils/messages.py
