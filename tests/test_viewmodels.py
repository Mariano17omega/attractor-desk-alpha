"""Tests for viewmodels."""

from pathlib import Path

from core.models import ThemeMode
from core.persistence import (
    ArtifactRepository,
    Database,
    MessageRepository,
    SessionRepository,
    WorkspaceRepository,
)
from ui.viewmodels.settings_viewmodel import SettingsViewModel
from ui.viewmodels.workspace_viewmodel import WorkspaceViewModel


def test_workspace_viewmodel_crud(tmp_path: Path) -> None:
    db = Database(tmp_path / "workspace.db")
    workspace_repo = WorkspaceRepository(db)
    session_repo = SessionRepository(db)
    message_repo = MessageRepository(db)
    artifact_repo = ArtifactRepository(db)

    viewmodel = WorkspaceViewModel(
        workspace_repository=workspace_repo,
        session_repository=session_repo,
        message_repository=message_repo,
        artifact_repository=artifact_repo,
    )

    viewmodel.create_workspace("Workspace A")
    assert len(viewmodel.workspaces) == 1
    assert viewmodel.current_workspace is not None

    session = viewmodel.create_session()
    assert session is not None
    assert len(viewmodel.sessions) == 1
    assert viewmodel.current_session is not None

    viewmodel.delete_session(session.id)
    assert len(viewmodel.sessions) == 0


def test_settings_viewmodel_persistence(tmp_path: Path) -> None:
    db = Database(tmp_path / "settings.db")
    settings_vm = SettingsViewModel(settings_db=db)
    settings_vm.theme_mode = ThemeMode.LIGHT
    settings_vm.font_family = "Arial"
    settings_vm.transparency = 85
    settings_vm.keep_above = True
    settings_vm.api_key = "test-key"
    settings_vm.default_model = "openai/gpt-4o"
    settings_vm.add_model("openai/gpt-4o")
    settings_vm.save_settings()

    reloaded = SettingsViewModel(settings_db=db)
    assert reloaded.theme_mode == ThemeMode.LIGHT
    assert reloaded.font_family == "Arial"
    assert reloaded.transparency == 85
    assert reloaded.keep_above is True
    assert reloaded.api_key == "test-key"
    assert reloaded.default_model == "openai/gpt-4o"


def test_settings_viewmodel_deep_search_persistence(tmp_path: Path) -> None:
    db = Database(tmp_path / "settings.db")
    settings_vm = SettingsViewModel(settings_db=db)
    settings_vm.deep_search_enabled = True
    settings_vm.exa_api_key = "exa-test-key-123"
    settings_vm.deep_search_num_results = 10
    settings_vm.save_settings()

    reloaded = SettingsViewModel(settings_db=db)
    assert reloaded.deep_search_enabled is True
    assert reloaded.exa_api_key == "exa-test-key-123"
    assert reloaded.deep_search_num_results == 10

