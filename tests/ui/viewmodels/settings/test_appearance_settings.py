"""Unit tests for AppearanceSettings."""

import pytest
from PySide6.QtCore import QObject

from core.models import ThemeMode
from core.persistence import Database
from ui.viewmodels.settings.appearance_settings import AppearanceSettings


@pytest.fixture
def temp_db(tmp_path):
    """Create temporary database for testing."""
    db_path = tmp_path / "test_settings.db"
    return Database(str(db_path))


@pytest.fixture
def appearance_settings(temp_db):
    """Create AppearanceSettings instance for testing."""
    return AppearanceSettings(database=temp_db)


def test_default_values(appearance_settings):
    """Test default appearance settings values."""
    assert appearance_settings.theme_mode == ThemeMode.DARK
    assert appearance_settings.font_family == "Segoe UI"
    assert appearance_settings.transparency == 100
    assert appearance_settings.keep_above is False


def test_theme_mode_change_emits_signal(appearance_settings, qtbot):
    """Test that changing theme mode emits signals."""
    with qtbot.waitSignal(appearance_settings.theme_changed) as blocker:
        appearance_settings.theme_mode = ThemeMode.LIGHT

    assert blocker.args[0] == ThemeMode.LIGHT
    assert appearance_settings.theme_mode == ThemeMode.LIGHT


def test_theme_mode_accepts_string(appearance_settings):
    """Test that theme mode can be set from string."""
    appearance_settings.theme_mode = "light"
    assert appearance_settings.theme_mode == ThemeMode.LIGHT


def test_theme_mode_invalid_defaults_to_dark(appearance_settings):
    """Test that invalid theme mode defaults to DARK."""
    appearance_settings.theme_mode = "invalid_mode"
    assert appearance_settings.theme_mode == ThemeMode.DARK


def test_transparency_clamped_to_range(appearance_settings):
    """Test that transparency is clamped to 30-100 range."""
    appearance_settings.transparency = 150
    assert appearance_settings.transparency == 100

    appearance_settings.transparency = 10
    assert appearance_settings.transparency == 30


def test_transparency_change_emits_signal(appearance_settings, qtbot):
    """Test that changing transparency emits signals."""
    with qtbot.waitSignal(appearance_settings.transparency_changed) as blocker:
        appearance_settings.transparency = 85

    assert blocker.args[0] == 85
    assert appearance_settings.transparency == 85


def test_keep_above_toggle(appearance_settings, qtbot):
    """Test keep above toggle functionality."""
    with qtbot.waitSignal(appearance_settings.keep_above_changed) as blocker:
        appearance_settings.keep_above = True

    assert blocker.args[0] is True
    assert appearance_settings.keep_above is True


def test_font_family_change(appearance_settings, qtbot):
    """Test font family change."""
    with qtbot.waitSignal(appearance_settings.settings_changed):
        appearance_settings.font_family = "Arial"

    assert appearance_settings.font_family == "Arial"


def test_save_and_load(appearance_settings, temp_db):
    """Test saving and loading appearance settings."""
    # Set custom values
    appearance_settings.theme_mode = ThemeMode.LIGHT
    appearance_settings.font_family = "Arial"
    appearance_settings.transparency = 75
    appearance_settings.keep_above = True

    # Save to database
    appearance_settings.save()

    # Create new instance and load
    new_instance = AppearanceSettings(database=temp_db)
    new_instance.load()

    # Verify values persisted
    assert new_instance.theme_mode == ThemeMode.LIGHT
    assert new_instance.font_family == "Arial"
    assert new_instance.transparency == 75
    assert new_instance.keep_above is True


def test_snapshot_and_restore(appearance_settings, qtbot):
    """Test snapshot and restore functionality."""
    # Set initial values
    appearance_settings.theme_mode = ThemeMode.LIGHT
    appearance_settings.transparency = 80

    # Create snapshot
    snapshot = appearance_settings.snapshot()

    # Change values
    appearance_settings.theme_mode = ThemeMode.DARK
    appearance_settings.transparency = 50

    # Restore from snapshot
    with qtbot.waitSignals(
        [
            appearance_settings.theme_changed,
            appearance_settings.transparency_changed,
        ],
        timeout=1000,
    ):
        appearance_settings.restore_snapshot(snapshot)

    # Verify restoration
    assert appearance_settings.theme_mode == ThemeMode.LIGHT
    assert appearance_settings.transparency == 80


def test_no_signal_on_same_value(appearance_settings, qtbot):
    """Test that setting the same value doesn't emit signals."""
    appearance_settings.transparency = 100

    # Setting same value should not emit signal
    with qtbot.assertNotEmitted(appearance_settings.transparency_changed):
        appearance_settings.transparency = 100


def test_empty_font_family_ignored(appearance_settings):
    """Test that empty font family is ignored."""
    original = appearance_settings.font_family
    appearance_settings.font_family = ""
    assert appearance_settings.font_family == original
