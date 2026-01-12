"""PySide6 Views for the UI layer."""

from .main_window import MainWindow
from .chat_panel import ChatPanel
from .sidebar import Sidebar
from .message_bubble import MessageBubble
from .workspace_memory_panel import WorkspaceMemoryPanel
from .styles import get_dark_theme_stylesheet, get_light_theme_stylesheet
from .configuration import ConfigurationDialog
from .region_selection_overlay import RegionSelectionOverlay
from .capture_preview_dialog import CapturePreviewDialog

__all__ = [
    "MainWindow",
    "ChatPanel",
    "Sidebar",
    "MessageBubble",
    "WorkspaceMemoryPanel",
    "ConfigurationDialog",
    "get_dark_theme_stylesheet",
    "get_light_theme_stylesheet",
    "RegionSelectionOverlay",
    "CapturePreviewDialog",
]
