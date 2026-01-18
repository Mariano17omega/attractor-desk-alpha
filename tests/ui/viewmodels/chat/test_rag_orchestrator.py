"""Unit tests for RagOrchestrator."""

import pytest
from unittest.mock import Mock, call

from ui.viewmodels.chat.rag_orchestrator import RagOrchestrator
from core.services.rag_service import RagIndexRequest
from core.types import (
    ArtifactCollectionV1,
    ArtifactEntry,
    ArtifactExportMeta,
    ArtifactV3,
    ArtifactMarkdownV3,
    ArtifactCodeV3,
)


@pytest.fixture
def mock_rag_service():
    """Create a mock RagService."""
    return Mock()


@pytest.fixture
def mock_artifact_repository():
    """Create a mock ArtifactRepository."""
    return Mock()


@pytest.fixture
def mock_settings_viewmodel():
    """Create a mock SettingsViewModel with RAG configuration."""
    settings = Mock()
    settings.rag_chunk_size_chars = 500
    settings.rag_chunk_overlap_chars = 50
    settings.rag_embedding_model = "openai/text-embedding-3-small"
    settings.rag_enabled = True
    settings.rag_k_vec = 5
    settings.rag_index_text_artifacts = True
    settings.api_key = "test_api_key"
    return settings


@pytest.fixture
def rag_orchestrator(mock_rag_service, mock_artifact_repository, mock_settings_viewmodel):
    """Create a RagOrchestrator instance with mocked dependencies."""
    return RagOrchestrator(
        rag_service=mock_rag_service,
        artifact_repository=mock_artifact_repository,
        settings_viewmodel=mock_settings_viewmodel,
    )


@pytest.fixture
def sample_text_artifact():
    """Create a sample text artifact."""
    return ArtifactV3(
        currentIndex=1,
        contents=[
            ArtifactMarkdownV3(
                index=1,
                type="text",
                title="Research Paper",
                fullMarkdown="# Introduction\n\nThis is a research paper...",
            ),
        ],
    )


@pytest.fixture
def sample_code_artifact():
    """Create a sample code artifact."""
    return ArtifactV3(
        currentIndex=1,
        contents=[
            ArtifactCodeV3(
                index=1,
                type="code",
                title="main.py",
                code="print('Hello')",
                language="python",
            ),
        ],
    )


@pytest.fixture
def sample_collection_with_text(sample_text_artifact):
    """Create a collection with a text artifact."""
    entry = ArtifactEntry(
        id="entry_123",
        artifact=sample_text_artifact,
        export_meta=ArtifactExportMeta(),
    )
    return ArtifactCollectionV1(
        version=1,
        artifacts=[entry],
        active_artifact_id="entry_123",
    )


@pytest.fixture
def sample_collection_with_code(sample_code_artifact):
    """Create a collection with a code artifact."""
    entry = ArtifactEntry(
        id="entry_code",
        artifact=sample_code_artifact,
        export_meta=ArtifactExportMeta(),
    )
    return ArtifactCollectionV1(
        version=1,
        artifacts=[entry],
        active_artifact_id="entry_code",
    )


class TestRagOrchestratorInitialization:
    """Test RagOrchestrator initialization."""

    def test_initialization(self, rag_orchestrator):
        """Test that RagOrchestrator initializes correctly."""
        assert rag_orchestrator._rag_service is not None
        assert rag_orchestrator._artifact_repository is not None
        assert rag_orchestrator._settings_viewmodel is not None

    def test_initialization_without_rag_service(
        self, mock_artifact_repository, mock_settings_viewmodel
    ):
        """Test initialization with no RagService (optional dependency)."""
        orchestrator = RagOrchestrator(
            rag_service=None,
            artifact_repository=mock_artifact_repository,
            settings_viewmodel=mock_settings_viewmodel,
        )
        assert orchestrator._rag_service is None


class TestIndexPdfArtifact:
    """Test index_pdf_artifact method."""

    def test_index_pdf_artifact_success(self, rag_orchestrator, mock_rag_service):
        """Test successful PDF artifact indexing."""
        rag_orchestrator.index_pdf_artifact(
            workspace_id="workspace_1",
            session_id="session_1",
            entry_id="entry_pdf",
            source_name="Document.pdf",
            content="# Converted Content\n\nThis is the converted PDF content.",
            source_path="/path/to/document.pdf",
        )

        # Verify index_artifact was called once
        mock_rag_service.index_artifact.assert_called_once()

        # Verify the request parameters
        call_args = mock_rag_service.index_artifact.call_args[0][0]
        assert isinstance(call_args, RagIndexRequest)
        assert call_args.workspace_id == "workspace_1"
        assert call_args.session_id == "session_1"
        assert call_args.artifact_entry_id == "entry_pdf"
        assert call_args.source_type == "pdf"
        assert call_args.source_name == "Document.pdf"
        assert call_args.source_path == "/path/to/document.pdf"
        assert call_args.content == "# Converted Content\n\nThis is the converted PDF content."
        assert call_args.chunk_size_chars == 500
        assert call_args.chunk_overlap_chars == 50
        assert call_args.embedding_model == "openai/text-embedding-3-small"
        assert call_args.embeddings_enabled is True
        assert call_args.api_key == "test_api_key"

    def test_index_pdf_artifact_without_source_path(
        self, rag_orchestrator, mock_rag_service
    ):
        """Test PDF indexing without source path."""
        rag_orchestrator.index_pdf_artifact(
            workspace_id="workspace_1",
            session_id="session_1",
            entry_id="entry_pdf",
            source_name="Document.pdf",
            content="# Content",
        )

        call_args = mock_rag_service.index_artifact.call_args[0][0]
        assert call_args.source_path is None

    def test_index_pdf_artifact_without_rag_service(
        self, mock_artifact_repository, mock_settings_viewmodel
    ):
        """Test that indexing does nothing when RagService is unavailable."""
        orchestrator = RagOrchestrator(
            rag_service=None,
            artifact_repository=mock_artifact_repository,
            settings_viewmodel=mock_settings_viewmodel,
        )

        # Should not raise errors
        orchestrator.index_pdf_artifact(
            workspace_id="workspace_1",
            session_id="session_1",
            entry_id="entry_pdf",
            source_name="Document.pdf",
            content="# Content",
        )

    def test_index_pdf_artifact_with_default_embedding_model(
        self, rag_orchestrator, mock_rag_service, mock_settings_viewmodel
    ):
        """Test PDF indexing with default embedding model."""
        mock_settings_viewmodel.rag_embedding_model = None

        rag_orchestrator.index_pdf_artifact(
            workspace_id="workspace_1",
            session_id="session_1",
            entry_id="entry_pdf",
            source_name="Document.pdf",
            content="# Content",
        )

        call_args = mock_rag_service.index_artifact.call_args[0][0]
        # Should use DEFAULT_EMBEDDING_MODEL
        assert call_args.embedding_model == "openai/text-embedding-3-small"

    def test_index_pdf_artifact_embeddings_disabled(
        self, rag_orchestrator, mock_rag_service, mock_settings_viewmodel
    ):
        """Test PDF indexing with embeddings disabled."""
        mock_settings_viewmodel.rag_enabled = False

        rag_orchestrator.index_pdf_artifact(
            workspace_id="workspace_1",
            session_id="session_1",
            entry_id="entry_pdf",
            source_name="Document.pdf",
            content="# Content",
        )

        call_args = mock_rag_service.index_artifact.call_args[0][0]
        assert call_args.embeddings_enabled is False


class TestIndexActiveTextArtifact:
    """Test index_active_text_artifact method."""

    def test_index_text_artifact_success(
        self,
        rag_orchestrator,
        mock_rag_service,
        mock_artifact_repository,
        sample_collection_with_text,
    ):
        """Test successful text artifact indexing."""
        mock_artifact_repository.get_collection.return_value = sample_collection_with_text

        rag_orchestrator.index_active_text_artifact(
            workspace_id="workspace_1",
            session_id="session_1",
        )

        # Verify index_artifact was called
        mock_rag_service.index_artifact.assert_called_once()

        # Verify the request parameters
        call_args = mock_rag_service.index_artifact.call_args[0][0]
        assert isinstance(call_args, RagIndexRequest)
        assert call_args.workspace_id == "workspace_1"
        assert call_args.session_id == "session_1"
        assert call_args.artifact_entry_id == "entry_123"
        assert call_args.source_type == "artifact"
        assert call_args.source_name == "Research Paper"
        assert call_args.content == "# Introduction\n\nThis is a research paper..."

    def test_index_text_artifact_without_rag_service(
        self, mock_artifact_repository, mock_settings_viewmodel
    ):
        """Test that indexing does nothing when RagService is unavailable."""
        orchestrator = RagOrchestrator(
            rag_service=None,
            artifact_repository=mock_artifact_repository,
            settings_viewmodel=mock_settings_viewmodel,
        )

        orchestrator.index_active_text_artifact(
            workspace_id="workspace_1",
            session_id="session_1",
        )

        # Should not raise errors
        mock_artifact_repository.get_collection.assert_not_called()

    def test_index_text_artifact_disabled_in_settings(
        self, rag_orchestrator, mock_rag_service, mock_settings_viewmodel
    ):
        """Test that indexing is skipped when disabled in settings."""
        mock_settings_viewmodel.rag_index_text_artifacts = False

        rag_orchestrator.index_active_text_artifact(
            workspace_id="workspace_1",
            session_id="session_1",
        )

        mock_rag_service.index_artifact.assert_not_called()

    def test_index_text_artifact_no_collection(
        self, rag_orchestrator, mock_rag_service, mock_artifact_repository
    ):
        """Test indexing when no artifact collection exists."""
        mock_artifact_repository.get_collection.return_value = None

        rag_orchestrator.index_active_text_artifact(
            workspace_id="workspace_1",
            session_id="session_1",
        )

        mock_rag_service.index_artifact.assert_not_called()

    def test_index_text_artifact_no_active_entry(
        self, rag_orchestrator, mock_rag_service, mock_artifact_repository
    ):
        """Test indexing when collection has no active entry."""
        empty_collection = ArtifactCollectionV1(
            version=1,
            artifacts=[],
            active_artifact_id=None,
        )
        mock_artifact_repository.get_collection.return_value = empty_collection

        rag_orchestrator.index_active_text_artifact(
            workspace_id="workspace_1",
            session_id="session_1",
        )

        mock_rag_service.index_artifact.assert_not_called()

    def test_index_text_artifact_code_artifact(
        self,
        rag_orchestrator,
        mock_rag_service,
        mock_artifact_repository,
        sample_collection_with_code,
    ):
        """Test that code artifacts are not indexed (only text artifacts)."""
        mock_artifact_repository.get_collection.return_value = sample_collection_with_code

        rag_orchestrator.index_active_text_artifact(
            workspace_id="workspace_1",
            session_id="session_1",
        )

        # Should not index code artifacts
        mock_rag_service.index_artifact.assert_not_called()

    def test_index_text_artifact_untitled(
        self,
        rag_orchestrator,
        mock_rag_service,
        mock_artifact_repository,
        sample_text_artifact,
    ):
        """Test indexing artifact with no title (uses 'Untitled')."""
        # Create artifact without title
        sample_text_artifact.contents[0].title = None
        entry = ArtifactEntry(
            id="entry_no_title",
            artifact=sample_text_artifact,
            export_meta=ArtifactExportMeta(),
        )
        collection = ArtifactCollectionV1(
            version=1,
            artifacts=[entry],
            active_artifact_id="entry_no_title",
        )
        mock_artifact_repository.get_collection.return_value = collection

        rag_orchestrator.index_active_text_artifact(
            workspace_id="workspace_1",
            session_id="session_1",
        )

        call_args = mock_rag_service.index_artifact.call_args[0][0]
        assert call_args.source_name == "Untitled"

    def test_index_text_artifact_empty_title(
        self,
        rag_orchestrator,
        mock_rag_service,
        mock_artifact_repository,
        sample_text_artifact,
    ):
        """Test indexing artifact with empty title (uses 'Untitled')."""
        sample_text_artifact.contents[0].title = ""
        entry = ArtifactEntry(
            id="entry_empty_title",
            artifact=sample_text_artifact,
            export_meta=ArtifactExportMeta(),
        )
        collection = ArtifactCollectionV1(
            version=1,
            artifacts=[entry],
            active_artifact_id="entry_empty_title",
        )
        mock_artifact_repository.get_collection.return_value = collection

        rag_orchestrator.index_active_text_artifact(
            workspace_id="workspace_1",
            session_id="session_1",
        )

        call_args = mock_rag_service.index_artifact.call_args[0][0]
        assert call_args.source_name == "Untitled"
