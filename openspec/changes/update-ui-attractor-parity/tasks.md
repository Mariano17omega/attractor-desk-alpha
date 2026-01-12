## 1. Implementation
- [x] 1.1 Copy reference styles and assets into ui/styles.py and ui/assets, and update asset loading paths in UI components.
- [x] 1.2 Add sqlite3 persistence layer for workspaces, sessions, messages, artifacts, and settings (schema + repositories).
- [x] 1.3 Implement Settings viewmodel and reference-style configuration dialog with functional Models/Theme pages and placeholder pages for Deep Research, RAG, Memory, and Shortcuts.
- [x] 1.4 Implement sessions/history sidebar UI and viewmodel, including workspace and session CRUD wired to persistence. (Depends on 1.2)
- [x] 1.5 Update ChatViewModel to load/save session messages and artifacts, and to react to active session changes. (Depends on 1.2, 1.4)
- [x] 1.6 Update main window layout to reference structure and wire memory button to toggle the artifacts panel, plus sidebar toggle behavior. (Depends on 1.4, 1.5)
- [x] 1.7 Apply theme selection to the main window and settings dialog, including transparency and keep-above behaviors. (Depends on 1.1, 1.3)
- [x] 1.8 Add unit tests for persistence repositories and session settings viewmodels.
- [x] 1.9 Validate manually: run pytest and verify main window layout, session CRUD/persistence, and settings dialog behavior.
