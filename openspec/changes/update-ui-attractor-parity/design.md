## Context
Open Canvas currently ships a simplified UI with a two-pane chat/artifacts split and a basic settings dialog. The attractor_desk_Reference app provides the target UI structure, panel hierarchy, and theme system. Achieving parity requires new UI components, a configuration dialog aligned to the reference, and persistent session history.

## Goals / Non-Goals
- Goals:
  - Match the reference main window layout and panel hierarchy.
  - Provide functional workspace/session management with persistence.
  - Replace the settings dialog with the reference configuration dialog and keep Models/Theme functional.
  - Apply reference themes and assets as the styling source of truth.
- Non-Goals:
  - Implement Deep Research, RAG, Memory, or Shortcuts behavior (placeholders only).
  - Change core graph behavior or LLM routing.
  - Introduce agent selection logic beyond UI placeholders.

## Decisions
- Main window layout: use a left-to-right QSplitter with chat panel, sessions/history sidebar, and artifacts panel on the right. The memory button in the chat header toggles the artifacts panel visibility while chat and sessions remain visible.
- Session persistence: introduce a lightweight persistence layer (sqlite3) to store workspaces, sessions, messages, and artifacts. Serialize artifacts using Pydantic model_dump/model_validate so versions can be restored per session.
- View models: add a Sessions/Workspace viewmodel and Settings viewmodel to keep UI state separate from core logic. Inject repositories into viewmodels to preserve MVVM separation.
- Settings dialog: replace the current settings dialog with a reference-style configuration dialog composed of sidebar navigation and stacked pages. Models and Theme pages persist changes; other pages render placeholders only.
- Theming and assets: copy Documentation/attractor_desk_Reference/views/styles.py into ui/styles.py and copy Documentation/attractor_desk_Reference/assets into ui/assets, updating UI components to load local assets.
- Branding text: set the main window title to `Attractor Desk` and the chat header labels to `AMADEUS CHANNEL` and `SECURE CONNECTION // AMADEUS PROTOCOL V1.02` to match the reference.

## Alternatives Considered
- JSON file persistence for sessions/messages: simpler to implement but harder to query and evolve; rejected in favor of sqlite3.
- Keeping the existing settings dialog and adding tabs: rejected because it diverges from the reference layout.

## Risks / Trade-offs
- Adding sqlite persistence increases complexity; mitigate with a minimal schema and repository tests.
- Placeholder pages may mislead users; mitigate with clear placeholder copy consistent with the reference.

## Migration Plan
- On first run, create a default workspace and session if none exist.
- If an in-memory chat exists when persistence is introduced, seed the default session with the current messages and artifacts.

## Open Questions
- None.
