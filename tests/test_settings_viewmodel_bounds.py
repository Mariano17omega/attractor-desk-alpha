"""Tests for SettingsViewModel validation and bounds."""

from pathlib import Path

from core.models import ThemeMode
from core.persistence import Database
from ui.viewmodels import SettingsViewModel


def test_settings_viewmodel_clamps_values(tmp_path: Path) -> None:
    db = Database(tmp_path / "settings.db")
    settings_vm = SettingsViewModel(settings_db=db)

    settings_vm.rag_chunk_overlap_chars = 300
    settings_vm.rag_chunk_size_chars = 250
    assert settings_vm.rag_chunk_overlap_chars == 249

    settings_vm.rag_chunk_size_chars = 100
    assert settings_vm.rag_chunk_size_chars == 200

    settings_vm.rag_chunk_overlap_chars = 500
    assert settings_vm.rag_chunk_overlap_chars == 199

    settings_vm.deep_search_num_results = 0
    assert settings_vm.deep_search_num_results == 1
    settings_vm.deep_search_num_results = 50
    assert settings_vm.deep_search_num_results == 20


def test_settings_viewmodel_validates_inputs(tmp_path: Path) -> None:
    db = Database(tmp_path / "settings.db")
    settings_vm = SettingsViewModel(settings_db=db)

    settings_vm.search_provider = "unknown"
    assert settings_vm.search_provider == "exa"

    settings_vm.theme_mode = "invalid"
    assert settings_vm.theme_mode == ThemeMode.DARK

    initial_models = settings_vm.models
    settings_vm.add_model("openai/gpt-4o")
    assert settings_vm.models == initial_models

    settings_vm.add_model(" new-model ")
    assert "new-model" in settings_vm.models
