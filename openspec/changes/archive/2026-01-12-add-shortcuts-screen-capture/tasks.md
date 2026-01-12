## 1. Implementation
- [x] 1.1 Add shortcut and attachment data models plus persistence tables/repository for attachment file paths
- [x] 1.2 Extend settings viewmodel to load/save shortcut bindings and expose update/reset APIs
- [x] 1.3 Add screen capture utilities and services (capture, image helpers, model capability checks)
- [x] 1.4 Implement region selection overlay and capture preview dialog widgets
- [x] 1.5 Integrate shortcut registration and capture flow into the main window
- [x] 1.6 Update chat viewmodel to handle pending attachments and include images in prompts
- [x] 1.7 Update chat panel to reflect send shortcut and show pending attachment previews
- [x] 1.8 Replace the Shortcuts placeholder page with the shortcuts configuration page
- [x] 1.9 Add dependency updates and document any manual verification steps

## Manual Verification
- Open Settings -> Shortcuts, edit and reset bindings, save, and confirm shortcuts update.
- Trigger full-screen and region capture, validate preview confirm/retake/cancel flows.
- Confirm captures show as pending thumbnails and attach on send for multimodal models.
- Confirm non-multimodal models show a warning and do not attach captures.
