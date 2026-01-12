# Change: Align Open Canvas UI with Attractor Desk reference

## Why
Open Canvas needs UI and UX parity with the attractor_desk_Reference desktop app so users see a familiar layout, navigation model, and theme behavior.

## What Changes
- Replace the main window layout to match the reference hierarchy, including chat, sessions/history sidebar, and right-side artifacts panel toggled by the memory button.
- Implement fully functional session/workspace management with persistent storage for sessions, messages, and artifacts.
- Replace the current settings dialog with the reference-style configuration dialog, keeping Models and Theme functional and other pages as placeholders.
- Adopt the reference theme definitions and assets (styles and icons/profile images) as the source of truth for styling.

## Impact
- Affected specs: render-main-window, manage-chat-sessions, settings-configuration, apply-ui-themes
- Affected code: ui/main_window.py, ui/widgets/*, ui/viewmodels/*, core/persistence/*, ui/styles.py, ui/assets/*
