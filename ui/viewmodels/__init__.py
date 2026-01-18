"""ViewModels package for Open Canvas UI."""

from ui.viewmodels.chat_viewmodel import ChatViewModel
from ui.viewmodels.main_viewmodel import MainViewModel
from ui.viewmodels.settings.coordinator import SettingsCoordinator
from ui.viewmodels.workspace_viewmodel import WorkspaceViewModel

# Backward compatibility alias
SettingsViewModel = SettingsCoordinator

__all__ = [
    "ChatViewModel",
    "MainViewModel",
    "SettingsCoordinator",
    "SettingsViewModel",  # Backward compatibility
    "WorkspaceViewModel",
]
