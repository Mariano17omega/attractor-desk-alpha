"""Tests for artifact collection persistence and export."""

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from core.persistence.artifact_repository import ArtifactRepository
from core.persistence.database import Database
from core.services.artifact_export_service import ArtifactExportService
from core.types import (
    ArtifactCollectionV1,
    ArtifactEntry,
    ArtifactExportMeta,
    ArtifactMarkdownV3,
    ArtifactCodeV3,
    ArtifactV3,
    ProgrammingLanguageOptions,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        yield db
        db.close()


@pytest.fixture
def test_session_id(temp_db):
    """Create a workspace and session for testing."""
    from datetime import datetime

    conn = temp_db.get_connection()
    workspace_id = str(uuid4())
    session_id = str(uuid4())
    now = datetime.now().isoformat()

    conn.execute(
        "INSERT INTO workspaces (id, name, created_at) VALUES (?, ?, ?)",
        (workspace_id, "Test Workspace", now),
    )
    conn.execute(
        "INSERT INTO sessions (id, workspace_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (session_id, workspace_id, "Test Session", now, now),
    )
    conn.commit()
    return session_id


@pytest.fixture
def artifact_repo(temp_db):
    """Create an artifact repository with temp database."""
    return ArtifactRepository(temp_db)


@pytest.fixture
def sample_text_artifact():
    """Create a sample text artifact."""
    content = ArtifactMarkdownV3(
        index=1,
        type="text",
        title="Test Text",
        fullMarkdown="# Test\n\nThis is test content.",
    )
    return ArtifactV3(currentIndex=1, contents=[content])


@pytest.fixture
def sample_code_artifact():
    """Create a sample code artifact."""
    content = ArtifactCodeV3(
        index=1,
        type="code",
        title="Test Code",
        language=ProgrammingLanguageOptions.PYTHON,
        code="def hello():\n    print('Hello')",
    )
    return ArtifactV3(currentIndex=1, contents=[content])


class TestArtifactCollectionPersistence:
    """Tests for artifact collection persistence."""

    def test_save_and_get_collection(self, artifact_repo, sample_text_artifact, test_session_id):
        """Test saving and retrieving a collection."""
        entry = ArtifactEntry(
            id=str(uuid4()),
            artifact=sample_text_artifact,
            export_meta=ArtifactExportMeta(),
        )
        collection = ArtifactCollectionV1(
            version=1,
            artifacts=[entry],
            active_artifact_id=entry.id,
        )

        artifact_repo.save_collection(test_session_id, collection)
        loaded = artifact_repo.get_collection(test_session_id)

        assert loaded is not None
        assert loaded.version == 1
        assert len(loaded.artifacts) == 1
        assert loaded.active_artifact_id == entry.id

    def test_legacy_artifact_migration(self, artifact_repo, sample_text_artifact, temp_db, test_session_id):
        """Test that legacy ArtifactV3 data is migrated to collection format."""
        # Manually insert legacy format
        import json
        from datetime import datetime

        legacy_json = json.dumps(
            sample_text_artifact.model_dump(by_alias=True, mode="json")
        )
        conn = temp_db.get_connection()
        conn.execute(
            """
            INSERT INTO artifacts (id, session_id, artifact_json, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (str(uuid4()), test_session_id, legacy_json, datetime.now().isoformat()),
        )
        conn.commit()

        # Load should return a collection
        loaded = artifact_repo.get_collection(test_session_id)

        assert loaded is not None
        assert loaded.version == 1
        assert len(loaded.artifacts) == 1
        assert loaded.active_artifact_id is not None

    def test_get_active_artifact(self, artifact_repo, sample_text_artifact, sample_code_artifact, test_session_id):
        """Test getting the active artifact from a collection."""
        entry1 = ArtifactEntry(
            id=str(uuid4()),
            artifact=sample_text_artifact,
            export_meta=ArtifactExportMeta(),
        )
        entry2 = ArtifactEntry(
            id=str(uuid4()),
            artifact=sample_code_artifact,
            export_meta=ArtifactExportMeta(),
        )
        collection = ArtifactCollectionV1(
            version=1,
            artifacts=[entry1, entry2],
            active_artifact_id=entry2.id,
        )

        artifact_repo.save_collection(test_session_id, collection)
        loaded = artifact_repo.get_collection(test_session_id)

        active = loaded.get_active_artifact()
        assert active is not None
        assert active.contents[0].type == "code"


class TestArtifactExportService:
    """Tests for artifact export service."""

    def test_export_text_artifact(self, artifact_repo, sample_text_artifact, test_session_id):
        """Test exporting a text artifact."""
        with tempfile.TemporaryDirectory() as tmpdir:
            entry = ArtifactEntry(
                id=str(uuid4()),
                artifact=sample_text_artifact,
                export_meta=ArtifactExportMeta(),
            )
            collection = ArtifactCollectionV1(
                version=1,
                artifacts=[entry],
                active_artifact_id=entry.id,
            )
            artifact_repo.save_collection(test_session_id, collection)

            export_service = ArtifactExportService(artifact_repo)
            export_service.set_export_dir(Path(tmpdir))

            exported = export_service.export_session(test_session_id, "Test Session")

            assert len(exported) == 1
            assert exported[0].exists()
            content = exported[0].read_text()
            assert "# Test" in content

    def test_export_code_artifact(self, artifact_repo, sample_code_artifact, test_session_id):
        """Test exporting a code artifact with fenced block."""
        with tempfile.TemporaryDirectory() as tmpdir:
            entry = ArtifactEntry(
                id=str(uuid4()),
                artifact=sample_code_artifact,
                export_meta=ArtifactExportMeta(),
            )
            collection = ArtifactCollectionV1(
                version=1,
                artifacts=[entry],
                active_artifact_id=entry.id,
            )
            artifact_repo.save_collection(test_session_id, collection)

            export_service = ArtifactExportService(artifact_repo)
            export_service.set_export_dir(Path(tmpdir))

            exported = export_service.export_session(test_session_id, "Test Session")

            assert len(exported) == 1
            content = exported[0].read_text()
            assert "```python" in content
            assert "def hello()" in content

    def test_pdf_export_unique_naming(self, artifact_repo, sample_text_artifact, test_session_id):
        """Test that PDF ingestions get unique filenames."""
        with tempfile.TemporaryDirectory() as tmpdir:
            entry = ArtifactEntry(
                id=str(uuid4()),
                artifact=sample_text_artifact,
                export_meta=ArtifactExportMeta(source_pdf="test_doc"),
            )
            collection = ArtifactCollectionV1(
                version=1,
                artifacts=[entry],
                active_artifact_id=entry.id,
            )
            artifact_repo.save_collection(test_session_id, collection)

            export_service = ArtifactExportService(artifact_repo)
            export_service.set_export_dir(Path(tmpdir))

            # First export
            exported1 = export_service.export_session(test_session_id, "Test")
            assert "test_doc.md" in str(exported1[0])

            # Reload collection (which now has stable filename)
            collection = artifact_repo.get_collection(test_session_id)

            # Create duplicate PDF import (different artifact, same source)
            entry2 = ArtifactEntry(
                id=str(uuid4()),
                artifact=sample_text_artifact,
                export_meta=ArtifactExportMeta(source_pdf="test_doc"),
            )
            collection.artifacts.append(entry2)
            artifact_repo.save_collection(test_session_id, collection)

            exported2 = export_service.export_session(test_session_id, "Test")
            # Should have test_doc.md (stable from first) and test_doc-2.md (new)
            filenames = [p.name for p in exported2]
            assert "test_doc.md" in filenames
            assert "test_doc-2.md" in filenames

