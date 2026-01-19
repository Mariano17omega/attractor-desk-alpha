"""Integration tests for SettingsCoordinator persistence."""

import pytest
from pathlib import Path
from core.models import ThemeMode
from core.persistence import Database
from ui.viewmodels.settings import SettingsCoordinator

@pytest.fixture
def db_path(tmp_path):
    """Provide a path for the test database."""
    return tmp_path / "settings_test.db"

@pytest.fixture
def db(db_path):
    """Provide a Database instance."""
    return Database(db_path)

def test_settings_persistence_cycle(db_path):
    """Test that settings persist correctly through save/load cycles."""
    # 1. Setup initial state
    db1 = Database(db_path)
    coordinator1 = SettingsCoordinator(database=db1)
    coordinator1.load_settings()

    original_theme = coordinator1.theme_mode
    original_rag = coordinator1.rag_enabled
    
    # 2. Change settings
    new_theme = ThemeMode.LIGHT if original_theme == ThemeMode.DARK else ThemeMode.DARK
    coordinator1.theme_mode = new_theme
    coordinator1.transparency = 75
    coordinator1.default_model = "openai/gpt-4o"
    coordinator1.rag_enabled = not original_rag
    coordinator1.deep_search_enabled = not coordinator1.deep_search_enabled
    coordinator1.rag_chunk_size_chars = 1500
    coordinator1.sidebar_visible = False

    # 3. Save
    coordinator1.save_settings()

    # 4. Reload in new instance (simulate app restart)
    db2 = Database(db_path)
    coordinator2 = SettingsCoordinator(database=db2)
    coordinator2.load_settings()

    # 5. Verify persistence
    assert coordinator2.theme_mode == new_theme
    assert coordinator2.transparency == 75
    assert coordinator2.default_model == "openai/gpt-4o"
    assert coordinator2.rag_enabled != original_rag
    assert coordinator2.rag_chunk_size_chars == 1500
    assert coordinator2.sidebar_visible is False

def test_revert_to_saved(db_path):
    """Test reverting settings to their saved state."""
    # Setup and save initial state
    db = Database(db_path)
    coordinator = SettingsCoordinator(database=db)
    coordinator.load_settings()
    
    coordinator.theme_mode = ThemeMode.DARK
    coordinator.transparency = 100
    coordinator.save_settings()

    # Make unsaved changes
    coordinator.theme_mode = ThemeMode.LIGHT
    coordinator.transparency = 50
    
    assert coordinator.theme_mode == ThemeMode.LIGHT
    assert coordinator.transparency == 50

    # Revert
    coordinator.revert_to_saved()

    # Verify reversion
    assert coordinator.theme_mode == ThemeMode.DARK
    assert coordinator.transparency == 100

def test_subsystem_delegation(db):
    """Test that facade properties correctly delegate to subsystems."""
    coordinator = SettingsCoordinator(database=db)
    coordinator.load_settings()

    # Test appearance delegation
    coordinator.appearance.transparency = 85
    assert coordinator.transparency == 85
    
    coordinator.transparency = 90
    assert coordinator.appearance.transparency == 90

    # Test models delegation
    coordinator.models.default_model = "anthropic/claude-3.5-sonnet"
    assert coordinator.default_model == "anthropic/claude-3.5-sonnet"

    coordinator.default_model = "openai/gpt-4-turbo"
    assert coordinator.models.default_model == "openai/gpt-4-turbo"

def test_shortcuts_persistence(db_path):
    """Test persistence of keyboard shortcuts."""
    # 1. Set shortcut
    db1 = Database(db_path)
    coord1 = SettingsCoordinator(database=db1)
    coord1.load_settings()
    
    coord1.set_shortcut_sequence("send_message", "Ctrl+Enter")
    coord1.save_settings()

    # 2. Reload and verify
    db2 = Database(db_path)
    coord2 = SettingsCoordinator(database=db2)
    coord2.load_settings()

    assert coord2.get_shortcut_sequence("send_message") == "Ctrl+Enter"

def test_backward_compatibility(db):
    """Test that the SettingsViewModel alias works for backward compatibility."""
    from ui.viewmodels import SettingsViewModel
    
    settings = SettingsViewModel(database=db)
    settings.load_settings()

    assert type(settings).__name__ == 'SettingsCoordinator'
    
    # Check property aliases
    assert hasattr(settings, 'theme_mode')
    assert hasattr(settings, 'transparency')
    assert hasattr(settings, 'default_model')
    assert hasattr(settings, 'rag_enabled')
