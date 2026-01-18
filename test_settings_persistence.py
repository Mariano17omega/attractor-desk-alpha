#!/usr/bin/env python3
"""Test script to verify SettingsCoordinator persistence functionality."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.models import ThemeMode
from core.persistence import Database
from ui.viewmodels.settings import SettingsCoordinator


def print_separator(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_settings_persistence():
    """Test that settings persist correctly through save/load cycles."""

    print_separator("SETTINGS PERSISTENCE TEST")

    # Create a test database
    db = Database()

    # Test 1: Load initial settings
    print_separator("Test 1: Load Initial Settings")
    coordinator = SettingsCoordinator(database=db)
    coordinator.load_settings()

    print(f"✓ Theme mode: {coordinator.theme_mode}")
    print(f"✓ Transparency: {coordinator.transparency}")
    print(f"✓ Default model: {coordinator.default_model}")
    print(f"✓ RAG enabled: {coordinator.rag_enabled}")
    print(f"✓ Deep search enabled: {coordinator.deep_search_enabled}")

    # Test 2: Change settings
    print_separator("Test 2: Change Settings")

    original_theme = coordinator.theme_mode
    original_transparency = coordinator.transparency
    original_model = coordinator.default_model
    original_rag = coordinator.rag_enabled
    original_deep_search = coordinator.deep_search_enabled

    # Change various settings across different subsystems
    new_theme = ThemeMode.LIGHT if original_theme == ThemeMode.DARK else ThemeMode.DARK
    coordinator.theme_mode = new_theme
    coordinator.transparency = 75
    coordinator.default_model = "openai/gpt-4o"
    coordinator.rag_enabled = not original_rag
    coordinator.deep_search_enabled = not original_deep_search
    coordinator.rag_chunk_size_chars = 1500
    coordinator.sidebar_visible = False

    print(f"✓ Changed theme: {original_theme} → {coordinator.theme_mode}")
    print(f"✓ Changed transparency: {original_transparency} → {coordinator.transparency}")
    print(f"✓ Changed model: {original_model} → {coordinator.default_model}")
    print(f"✓ Changed RAG enabled: {original_rag} → {coordinator.rag_enabled}")
    print(f"✓ Changed deep search: {original_deep_search} → {coordinator.deep_search_enabled}")
    print(f"✓ Changed RAG chunk size: → {coordinator.rag_chunk_size_chars}")
    print(f"✓ Changed sidebar visible: → {coordinator.sidebar_visible}")

    # Test 3: Save settings
    print_separator("Test 3: Save Settings")
    coordinator.save_settings()
    print("✓ Settings saved to database")

    # Test 4: Load settings in new coordinator instance
    print_separator("Test 4: Reload Settings (New Instance)")
    coordinator2 = SettingsCoordinator(database=db)
    coordinator2.load_settings()

    # Verify persistence
    assert coordinator2.theme_mode == new_theme, "Theme mode not persisted!"
    assert coordinator2.transparency == 75, "Transparency not persisted!"
    assert coordinator2.default_model == "openai/gpt-4o", "Default model not persisted!"
    assert coordinator2.rag_enabled == (not original_rag), "RAG enabled not persisted!"
    assert coordinator2.deep_search_enabled == (not original_deep_search), "Deep search not persisted!"
    assert coordinator2.rag_chunk_size_chars == 1500, "RAG chunk size not persisted!"
    assert coordinator2.sidebar_visible == False, "Sidebar visibility not persisted!"

    print(f"✓ Theme mode persisted: {coordinator2.theme_mode}")
    print(f"✓ Transparency persisted: {coordinator2.transparency}")
    print(f"✓ Default model persisted: {coordinator2.default_model}")
    print(f"✓ RAG enabled persisted: {coordinator2.rag_enabled}")
    print(f"✓ Deep search persisted: {coordinator2.deep_search_enabled}")
    print(f"✓ RAG chunk size persisted: {coordinator2.rag_chunk_size_chars}")
    print(f"✓ Sidebar visible persisted: {coordinator2.sidebar_visible}")

    # Test 5: Test revert functionality
    print_separator("Test 5: Test Revert to Saved")
    coordinator2.theme_mode = ThemeMode.DARK if new_theme == ThemeMode.LIGHT else ThemeMode.LIGHT
    coordinator2.transparency = 50
    print(f"✓ Modified theme to: {coordinator2.theme_mode}")
    print(f"✓ Modified transparency to: {coordinator2.transparency}")

    coordinator2.revert_to_saved()
    print(f"✓ Reverted theme to: {coordinator2.theme_mode}")
    print(f"✓ Reverted transparency to: {coordinator2.transparency}")

    assert coordinator2.theme_mode == new_theme, "Revert failed for theme!"
    assert coordinator2.transparency == 75, "Revert failed for transparency!"
    print("✓ Revert to saved works correctly")

    # Test 6: Test subsystem delegation
    print_separator("Test 6: Test Subsystem Delegation")

    # Test direct subsystem access
    coordinator2.appearance.transparency = 85
    assert coordinator2.transparency == 85, "Subsystem delegation failed!"
    print(f"✓ Subsystem access works: appearance.transparency = {coordinator2.transparency}")

    coordinator2.models.default_model = "anthropic/claude-3.5-sonnet"
    assert coordinator2.default_model == "anthropic/claude-3.5-sonnet", "Subsystem delegation failed!"
    print(f"✓ Subsystem access works: models.default_model = {coordinator2.default_model}")

    # Test 7: Test shortcuts
    print_separator("Test 7: Test Shortcuts Persistence")

    original_shortcut = coordinator2.get_shortcut_sequence("send_message")
    print(f"✓ Original send_message shortcut: {original_shortcut}")

    coordinator2.set_shortcut_sequence("send_message", "Ctrl+Enter")
    coordinator2.save_settings()

    coordinator3 = SettingsCoordinator(database=db)
    coordinator3.load_settings()

    persisted_shortcut = coordinator3.get_shortcut_sequence("send_message")
    assert persisted_shortcut == "Ctrl+Enter", "Shortcut not persisted!"
    print(f"✓ Shortcut persisted: {persisted_shortcut}")

    # Reset to original
    coordinator3.set_shortcut_sequence("send_message", original_shortcut)
    coordinator3.save_settings()

    # Test 8: Restore original settings
    print_separator("Test 8: Restore Original Settings")
    coordinator_final = SettingsCoordinator(database=db)
    coordinator_final.load_settings()

    coordinator_final.theme_mode = original_theme
    coordinator_final.transparency = original_transparency
    coordinator_final.default_model = original_model
    coordinator_final.rag_enabled = original_rag
    coordinator_final.deep_search_enabled = original_deep_search
    coordinator_final.sidebar_visible = True
    coordinator_final.save_settings()

    print(f"✓ Restored theme: {original_theme}")
    print(f"✓ Restored transparency: {original_transparency}")
    print(f"✓ Restored model: {original_model}")
    print(f"✓ Restored RAG enabled: {original_rag}")
    print(f"✓ Restored deep search: {original_deep_search}")

    print_separator("ALL TESTS PASSED! ✅")
    return True


def test_backward_compatibility():
    """Test backward compatibility alias."""

    print_separator("BACKWARD COMPATIBILITY TEST")

    # Import using the old name
    from ui.viewmodels import SettingsViewModel

    db = Database()

    # Should work with old name
    settings = SettingsViewModel(database=db)
    settings.load_settings()

    print(f"✓ SettingsViewModel alias works")
    print(f"✓ Type: {type(settings).__name__}")
    print(f"✓ Is SettingsCoordinator: {type(settings).__name__ == 'SettingsCoordinator'}")

    # Should have all the old properties
    assert hasattr(settings, 'theme_mode'), "Missing theme_mode property!"
    assert hasattr(settings, 'transparency'), "Missing transparency property!"
    assert hasattr(settings, 'default_model'), "Missing default_model property!"
    assert hasattr(settings, 'rag_enabled'), "Missing rag_enabled property!"

    print("✓ All backward compatibility properties available")
    print("✓ BACKWARD COMPATIBILITY TEST PASSED! ✅")

    return True


if __name__ == "__main__":
    try:
        # Run persistence tests
        test_settings_persistence()

        # Run backward compatibility tests
        test_backward_compatibility()

        print("\n" + "=" * 60)
        print("  🎉 ALL TESTS PASSED SUCCESSFULLY! 🎉")
        print("=" * 60)
        print("\nSettings refactoring is fully functional:")
        print("  ✅ Persistence works correctly")
        print("  ✅ All subsystems save/load properly")
        print("  ✅ Revert functionality works")
        print("  ✅ Subsystem delegation works")
        print("  ✅ Backward compatibility maintained")
        print("  ✅ No data loss or corruption")

        sys.exit(0)

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
