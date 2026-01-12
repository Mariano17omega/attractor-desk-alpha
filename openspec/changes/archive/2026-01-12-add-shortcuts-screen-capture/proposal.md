# Change: Add keyboard shortcuts, screen capture, and shortcut settings

## Why
Users need in-app keyboard shortcuts and a full screen capture flow with configurable bindings.

## What Changes
- Add configurable keyboard shortcut bindings persisted in settings.
- Implement screen capture flow (region selection, preview, confirm) and attach captures to prompts for multimodal models.
- Store capture files on disk at `/home/m/Documents/Attractor_Imagens` and persist only file references in the database.
- Replace the Shortcuts placeholder page with a functional shortcuts configuration page.

## Impact
- Affected specs: settings-configuration (modified), keyboard-shortcuts (new), screen-capture (new)
- Affected code: core/models, core/persistence, ui/viewmodels, ui/widgets, new ui infrastructure services
- Dependencies: add `mss` for screen capture
