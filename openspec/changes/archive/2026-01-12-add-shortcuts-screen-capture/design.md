## Context
The app currently reuses the reference UI layout but lacks keyboard shortcuts, screen capture, and shortcut configuration. We will reuse the reference implementations while aligning with the current core/ui separation and settings persistence model.

## Goals / Non-Goals
- Goals:
  - Provide in-app keyboard shortcuts and a configurable Shortcuts page.
  - Implement capture flow (region/full screen, preview, confirm) and attach captures to prompts when the model is multimodal.
  - Save images to `/home/m/Documents/Attractor_Imagens` and persist only file path references.
- Non-Goals:
  - Global OS-level hotkeys.
  - Storing image bytes inside the database.
  - Introducing new capture retention/cleanup features beyond the fixed path.

## Decisions
- Implement shortcuts with `QShortcut` in the main window and update bindings when settings change.
- Add a lightweight model-capabilities service (OpenRouter models endpoint) to detect multimodal support and fall back to name heuristics when offline.
- Store capture files on disk and persist only metadata + file paths in a new `message_attachments` table.
- Add UI-side capture services and widgets under `ui/` to keep Qt dependencies out of `core/`.

## Risks / Trade-offs
- OpenRouter capabilities lookup requires network access; fallback heuristics reduce false negatives but may be incomplete.
- Adding attachment persistence increases schema surface and requires careful handling of missing files.

## Migration Plan
- Extend SQLite schema with `message_attachments` table using `CREATE TABLE IF NOT EXISTS` to avoid breaking existing databases.
- Default to the fixed capture path and create it on first use.

## Open Questions
- None.
