"""ViewModels package for Open Canvas UI."""

# Import SettingsCoordinator first to avoid circular imports
from ui.viewmodels.settings.coordinator import SettingsCoordinator

# Backward compatibility alias
SettingsViewModel = SettingsCoordinator

# Import other viewmodels after SettingsViewModel is defined
from ui.viewmodels.chat_viewmodel import ChatViewModel
from ui.viewmodels.main_viewmodel import MainViewModel
from ui.viewmodels.workspace_viewmodel import WorkspaceViewModel

__all__ = [
    "ChatViewModel",
    "MainViewModel",
    "SettingsCoordinator",
    "SettingsViewModel",  # Backward compatibility
    "WorkspaceViewModel",
]
