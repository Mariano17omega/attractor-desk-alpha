"""Tests for persistence repositories."""

from pathlib import Path

from core.models import Message, MessageRole, Session, Workspace
from core.persistence import (
    ArtifactRepository,
    Database,
    MessageRepository,
    SessionRepository,
    SettingsRepository,
    WorkspaceRepository,
)
from core.types import ArtifactMarkdownV3, ArtifactV3


def test_persistence_roundtrip(tmp_path: Path) -> None:
    db = Database(tmp_path / "test.db")
    workspace_repo = WorkspaceRepository(db)
    session_repo = SessionRepository(db)
    message_repo = MessageRepository(db)
    artifact_repo = ArtifactRepository(db)
    settings_repo = SettingsRepository(db)

    workspace = Workspace.create("Test Workspace")
    workspace_repo.create(workspace)
    fetched_workspace = workspace_repo.get_by_id(workspace.id)
    assert fetched_workspace is not None
    assert fetched_workspace.name == "Test Workspace"

    session = Session.create(workspace.id, title="Session One")
    session_repo.create(session)
    sessions = session_repo.get_by_workspace(workspace.id)
    assert len(sessions) == 1
    assert sessions[0].title == "Session One"

    message = Message.create(session.id, MessageRole.USER, "Hello")
    message_repo.add(message)
    messages = message_repo.get_by_session(session.id)
    assert len(messages) == 1
    assert messages[0].content == "Hello"

    artifact = ArtifactV3(
        current_index=1,
        contents=[
            ArtifactMarkdownV3(
                index=1,
                title="Doc",
                full_markdown="Hi there",
            )
        ],
    )
    artifact_repo.save_for_session(session.id, artifact)
    loaded_artifact = artifact_repo.get_for_session(session.id)
    assert loaded_artifact is not None
    assert loaded_artifact.model_dump() == artifact.model_dump()

    settings_repo.set("theme.mode", "dark", "theme")
    assert settings_repo.get_value("theme.mode") == "dark"
