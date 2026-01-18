"""Unit tests for ChatPdfService."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from uuid import UUID

from ui.viewmodels.chat.chatpdf_service import ChatPdfService
from core.services.local_rag_service import LocalRagIndexRequest, LocalRagIndexResult
from core.types import (
    ArtifactCollectionV1,
    ArtifactEntry,
    ArtifactExportMeta,
    ArtifactV3,
    ArtifactPdfV1,
    ArtifactMarkdownV3,
)


@pytest.fixture
def mock_local_rag_service():
    """Create a mock LocalRagService."""
    service = Mock()
    service.is_busy = Mock(return_value=False)
    service.index_complete = Mock()
    service.index_error = Mock()
    return service


@pytest.fixture
def mock_artifact_repository():
    """Create a mock ArtifactRepository."""
    return Mock()


@pytest.fixture
def mock_artifact_viewmodel():
    """Create a mock ArtifactViewModel."""
    viewmodel = Mock()
    viewmodel._conversation_mode = "normal"
    viewmodel._active_pdf_document_id = None
    return viewmodel


@pytest.fixture
def mock_settings_viewmodel():
    """Create a mock SettingsViewModel with RAG configuration."""
    settings = Mock()
    settings.rag_chunk_size_chars = 500
    settings.rag_chunk_overlap_chars = 50
    settings.rag_embedding_model = "openai/text-embedding-3-small"
    settings.rag_enabled = True
    settings.rag_k_vec = 5
    settings.api_key = "test_api_key"
    return settings


@pytest.fixture
def chatpdf_service(
    mock_local_rag_service,
    mock_artifact_repository,
    mock_artifact_viewmodel,
    mock_settings_viewmodel,
):
    """Create a ChatPdfService instance with mocked dependencies."""
    return ChatPdfService(
        local_rag_service=mock_local_rag_service,
        artifact_repository=mock_artifact_repository,
        artifact_viewmodel=mock_artifact_viewmodel,
        settings_viewmodel=mock_settings_viewmodel,
    )


@pytest.fixture
def successful_index_result():
    """Create a successful indexing result."""
    return LocalRagIndexResult(
        success=True,
        document_id="doc_123",
        saved_path="/path/to/saved/document.pdf",
        error_message="",
    )


@pytest.fixture
def failed_index_result():
    """Create a failed indexing result."""
    return LocalRagIndexResult(
        success=False,
        document_id="",
        saved_path="",
        error_message="Failed to index PDF",
    )


class TestChatPdfServiceInitialization:
    """Test ChatPdfService initialization."""

    def test_initialization_with_service(self, chatpdf_service):
        """Test that ChatPdfService initializes correctly with LocalRagService."""
        assert chatpdf_service._local_rag_service is not None
        assert chatpdf_service._artifact_repository is not None
        assert chatpdf_service._artifact_viewmodel is not None
        assert chatpdf_service._settings_viewmodel is not None
        assert chatpdf_service._pending_chatpdf_path is None
        assert chatpdf_service._current_workspace_id is None
        assert chatpdf_service._current_session_id is None

    def test_initialization_without_service(
        self, mock_artifact_repository, mock_artifact_viewmodel, mock_settings_viewmodel
    ):
        """Test initialization without LocalRagService."""
        service = ChatPdfService(
            local_rag_service=None,
            artifact_repository=mock_artifact_repository,
            artifact_viewmodel=mock_artifact_viewmodel,
            settings_viewmodel=mock_settings_viewmodel,
        )
        assert service._local_rag_service is None

    def test_signals_connected(self, chatpdf_service, mock_local_rag_service):
        """Test that LocalRagService signals are connected."""
        # Verify signals were connected during init
        mock_local_rag_service.index_complete.connect.assert_called()
        mock_local_rag_service.index_error.connect.assert_called()


class TestOpenChatPdf:
    """Test open_chatpdf method."""

    def test_open_chatpdf_success(
        self, chatpdf_service, qtbot, mock_local_rag_service
    ):
        """Test successful ChatPDF opening."""
        with qtbot.waitSignal(chatpdf_service.chatpdf_status):
            chatpdf_service.open_chatpdf(
                pdf_path="/path/to/document.pdf",
                workspace_id="workspace_1",
                session_id="session_1",
            )

        # Verify indexing was started
        mock_local_rag_service.index_pdf.assert_called_once()
        call_args = mock_local_rag_service.index_pdf.call_args[0][0]
        assert isinstance(call_args, LocalRagIndexRequest)
        assert call_args.workspace_id == "workspace_1"
        assert call_args.session_id == "session_1"
        assert call_args.pdf_path == "/path/to/document.pdf"
        assert call_args.chunk_size_chars == 500
        assert call_args.chunk_overlap_chars == 50
        assert call_args.embedding_model == "openai/text-embedding-3-small"
        assert call_args.embeddings_enabled is True
        assert call_args.api_key == "test_api_key"

        # Verify state was set
        assert chatpdf_service._pending_chatpdf_path == "/path/to/document.pdf"
        assert chatpdf_service._current_workspace_id == "workspace_1"
        assert chatpdf_service._current_session_id == "session_1"

    def test_open_chatpdf_without_service(
        self, mock_artifact_repository, mock_artifact_viewmodel, mock_settings_viewmodel, qtbot
    ):
        """Test opening ChatPDF when LocalRagService is unavailable."""
        service = ChatPdfService(
            local_rag_service=None,
            artifact_repository=mock_artifact_repository,
            artifact_viewmodel=mock_artifact_viewmodel,
            settings_viewmodel=mock_settings_viewmodel,
        )

        with qtbot.waitSignal(service.error_occurred) as blocker:
            service.open_chatpdf(
                pdf_path="/path/to/document.pdf",
                workspace_id="workspace_1",
                session_id="session_1",
            )

        assert "unavailable" in blocker.args[0]

    def test_open_chatpdf_when_busy(
        self, chatpdf_service, qtbot, mock_local_rag_service
    ):
        """Test opening ChatPDF when service is already busy."""
        mock_local_rag_service.is_busy.return_value = True

        with qtbot.waitSignal(chatpdf_service.error_occurred) as blocker:
            chatpdf_service.open_chatpdf(
                pdf_path="/path/to/document.pdf",
                workspace_id="workspace_1",
                session_id="session_1",
            )

        assert "already in progress" in blocker.args[0]
        mock_local_rag_service.index_pdf.assert_not_called()

    def test_open_chatpdf_with_default_embedding_model(
        self, chatpdf_service, mock_local_rag_service, mock_settings_viewmodel
    ):
        """Test ChatPDF with default embedding model."""
        mock_settings_viewmodel.rag_embedding_model = None

        chatpdf_service.open_chatpdf(
            pdf_path="/path/to/document.pdf",
            workspace_id="workspace_1",
            session_id="session_1",
        )

        call_args = mock_local_rag_service.index_pdf.call_args[0][0]
        # Should use DEFAULT_EMBEDDING_MODEL
        assert call_args.embedding_model == "openai/text-embedding-3-small"


class TestIndexComplete:
    """Test _on_index_complete method."""

    @patch("ui.viewmodels.chat.chatpdf_service.uuid4")
    def test_index_complete_success(
        self,
        mock_uuid4,
        chatpdf_service,
        qtbot,
        mock_artifact_repository,
        mock_artifact_viewmodel,
        successful_index_result,
    ):
        """Test successful PDF indexing completion."""
        mock_uuid = UUID("12345678-1234-5678-1234-567812345678")
        mock_uuid4.return_value = mock_uuid
        mock_artifact_repository.get_collection.return_value = None

        # Set state as if open_chatpdf was called
        chatpdf_service._pending_chatpdf_path = "/path/to/document.pdf"
        chatpdf_service._current_workspace_id = "workspace_1"
        chatpdf_service._current_session_id = "session_1"

        with qtbot.waitSignals(
            [chatpdf_service.chatpdf_status, mock_artifact_viewmodel.set_artifact],
            timeout=1000,
        ):
            chatpdf_service._on_index_complete(successful_index_result)

        # Verify artifact was created and saved
        mock_artifact_repository.save_collection.assert_called_once()
        call_args = mock_artifact_repository.save_collection.call_args
        assert call_args[0][0] == "session_1"
        collection = call_args[0][1]
        assert isinstance(collection, ArtifactCollectionV1)
        assert len(collection.artifacts) == 1
        assert collection.artifacts[0].id == str(mock_uuid)

        # Verify PDF artifact was created
        artifact = mock_artifact_viewmodel.set_artifact.call_args[0][0]
        assert isinstance(artifact, ArtifactV3)
        assert len(artifact.contents) == 1
        pdf_content = artifact.contents[0]
        assert isinstance(pdf_content, ArtifactPdfV1)
        assert pdf_content.title == "document"
        assert pdf_content.pdf_path == "/path/to/saved/document.pdf"
        assert pdf_content.rag_document_id == "doc_123"

        # Verify conversation mode was updated
        assert mock_artifact_viewmodel._conversation_mode == "chatpdf"
        assert mock_artifact_viewmodel._active_pdf_document_id == "doc_123"

        # Verify state was cleaned up
        assert chatpdf_service._pending_chatpdf_path is None
        assert chatpdf_service._current_workspace_id is None
        assert chatpdf_service._current_session_id is None

    @patch("ui.viewmodels.chat.chatpdf_service.uuid4")
    def test_index_complete_appends_to_existing_collection(
        self,
        mock_uuid4,
        chatpdf_service,
        mock_artifact_repository,
        successful_index_result,
    ):
        """Test that PDF artifact is appended to existing collection."""
        mock_uuid = UUID("12345678-1234-5678-1234-567812345678")
        mock_uuid4.return_value = mock_uuid

        # Create existing collection
        existing_artifact = ArtifactV3(
            currentIndex=1,
            contents=[
                ArtifactMarkdownV3(
                    index=1, type="text", title="Existing", fullMarkdown="# Content"
                )
            ],
        )
        existing_entry = ArtifactEntry(
            id="existing_entry",
            artifact=existing_artifact,
            export_meta=ArtifactExportMeta(),
        )
        existing_collection = ArtifactCollectionV1(
            version=1,
            artifacts=[existing_entry],
            active_artifact_id="existing_entry",
        )
        mock_artifact_repository.get_collection.return_value = existing_collection

        chatpdf_service._current_session_id = "session_1"
        chatpdf_service._on_index_complete(successful_index_result)

        # Verify artifact was appended
        call_args = mock_artifact_repository.save_collection.call_args
        collection = call_args[0][1]
        assert len(collection.artifacts) == 2
        assert collection.artifacts[0].id == "existing_entry"
        assert collection.artifacts[1].id == str(mock_uuid)
        assert collection.active_artifact_id == str(mock_uuid)

    def test_index_complete_failure(
        self, chatpdf_service, qtbot, failed_index_result
    ):
        """Test handling of failed PDF indexing."""
        chatpdf_service._pending_chatpdf_path = "/path/to/document.pdf"
        chatpdf_service._current_workspace_id = "workspace_1"
        chatpdf_service._current_session_id = "session_1"

        with qtbot.waitSignals(
            [chatpdf_service.error_occurred, chatpdf_service.chatpdf_status],
            timeout=1000,
        ):
            chatpdf_service._on_index_complete(failed_index_result)

        # Verify state was cleaned up
        assert chatpdf_service._pending_chatpdf_path is None

    def test_index_complete_no_session(
        self, chatpdf_service, qtbot, successful_index_result
    ):
        """Test index complete when no session is active."""
        chatpdf_service._current_session_id = None

        with qtbot.waitSignals(
            [chatpdf_service.error_occurred, chatpdf_service.chatpdf_status],
            timeout=1000,
        ):
            chatpdf_service._on_index_complete(successful_index_result)

        assert chatpdf_service._pending_chatpdf_path is None


class TestIndexError:
    """Test _on_index_error method."""

    def test_index_error(self, chatpdf_service, qtbot):
        """Test handling of indexing errors."""
        chatpdf_service._pending_chatpdf_path = "/path/to/document.pdf"
        chatpdf_service._current_workspace_id = "workspace_1"
        chatpdf_service._current_session_id = "session_1"

        with qtbot.waitSignals(
            [chatpdf_service.error_occurred, chatpdf_service.chatpdf_status],
            timeout=1000,
        ) as blocker:
            chatpdf_service._on_index_error("Indexing failed")

        assert blocker.args[0][0] == "Indexing failed"
        assert blocker.args[1][0] == ""

        # Verify state was cleaned up
        assert chatpdf_service._pending_chatpdf_path is None


class TestIsBusy:
    """Test is_busy method."""

    def test_is_busy_when_indexing(self, chatpdf_service, mock_local_rag_service):
        """Test is_busy returns True when indexing is in progress."""
        mock_local_rag_service.is_busy.return_value = True
        assert chatpdf_service.is_busy() is True

    def test_is_busy_when_idle(self, chatpdf_service, mock_local_rag_service):
        """Test is_busy returns False when no indexing is in progress."""
        mock_local_rag_service.is_busy.return_value = False
        assert chatpdf_service.is_busy() is False

    def test_is_busy_without_service(
        self, mock_artifact_repository, mock_artifact_viewmodel, mock_settings_viewmodel
    ):
        """Test is_busy when LocalRagService is unavailable."""
        service = ChatPdfService(
            local_rag_service=None,
            artifact_repository=mock_artifact_repository,
            artifact_viewmodel=mock_artifact_viewmodel,
            settings_viewmodel=mock_settings_viewmodel,
        )
        assert service.is_busy() is False
