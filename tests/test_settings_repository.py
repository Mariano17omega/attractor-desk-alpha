"""Tests for settings repository helpers."""

from pathlib import Path

from core.persistence import Database
from core.persistence.settings_repository import SettingsRepository


def test_settings_repository_helpers(tmp_path: Path) -> None:
    db = Database(tmp_path / "settings.db")
    repo = SettingsRepository(db)

    repo.set("int.value", "not-int", "test")
    assert repo.get_int("int.value", 7) == 7

    repo.set("bool.true", "Yes", "test")
    repo.set("bool.false", "0", "test")
    assert repo.get_bool("bool.true", False) is True
    assert repo.get_bool("bool.false", True) is False

    assert repo.delete("bool.false") is True
    assert repo.delete("missing") is False


def test_settings_repository_collections(tmp_path: Path) -> None:
    db = Database(tmp_path / "settings.db")
    repo = SettingsRepository(db)

    repo.set("alpha.one", "1", "alpha")
    repo.set("alpha.two", "2", "alpha")
    repo.set("beta.one", "3", "beta")

    alpha_settings = repo.get_by_category("alpha")
    assert [setting.key for setting in alpha_settings] == ["alpha.one", "alpha.two"]

    all_settings = repo.get_all()
    keys = [setting.key for setting in all_settings]
    assert keys == ["alpha.one", "alpha.two", "beta.one"]
