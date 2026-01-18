"""Unit tests for PdfHandler."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import UUID

from ui.viewmodels.chat.pdf_handler import PdfHandler
from core.services.docling_service import PdfConversionResult
from core.types import (
    ArtifactCollectionV1,
    ArtifactEntry,
    ArtifactExportMeta,
    ArtifactV3,
    ArtifactMarkdownV3,
)


@pytest.fixture
def mock_artifact_repository():
    """Create a mock ArtifactRepository."""
    return Mock()


@pytest.fixture
def mock_artifact_viewmodel():
    """Create a mock ArtifactViewModel."""
    return Mock()


@pytest.fixture
def mock_rag_orchestrator():
    """Create a mock RagOrchestrator."""
    return Mock()


@pytest.fixture
def pdf_handler(
    mock_artifact_repository,
    mock_artifact_viewmodel,
    mock_rag_orchestrator,
):
    """Create a PdfHandler instance with mocked dependencies."""
    return PdfHandler(
        artifact_repository=mock_artifact_repository,
        artifact_viewmodel=mock_artifact_viewmodel,
        rag_orchestrator=mock_rag_orchestrator,
    )


@pytest.fixture
def successful_conversion_result():
    """Create a successful PDF conversion result."""
    return PdfConversionResult(
        success=True,
        markdown="# Converted Content\n\nThis is the converted PDF text.",
        source_filename="document.pdf",
        error_message="",
    )


@pytest.fixture
def failed_conversion_result():
    """Create a failed PDF conversion result."""
    return PdfConversionResult(
        success=False,
        markdown="",
        source_filename="document.pdf",
        error_message="Failed to convert PDF",
    )


class TestPdfHandlerInitialization:
    """Test PdfHandler initialization."""

    def test_initialization(self, pdf_handler):
        """Test that PdfHandler initializes correctly."""
        assert pdf_handler._artifact_repository is not None
        assert pdf_handler._artifact_viewmodel is not None
        assert pdf_handler._rag_orchestrator is not None
        assert pdf_handler._docling_service is not None
        assert pdf_handler._pending_pdf_path is None
        assert pdf_handler._current_workspace_id is None
        assert pdf_handler._current_session_id is None

    def test_docling_service_signal_connected(self, pdf_handler):
        """Test that DoclingService signals are connected."""
        # The signal should be connected to _on_pdf_conversion_complete
        assert pdf_handler._docling_service.conversion_complete.receivers(
            pdf_handler._on_pdf_conversion_complete
        )


class TestImportPdf:
    """Test import_pdf method."""

    def test_import_pdf_success(self, pdf_handler, qtbot):
        """Test successful PDF import initiation."""
        pdf_handler._docling_service.is_busy = Mock(return_value=False)
        pdf_handler._docling_service.convert_pdf = Mock()

        with qtbot.waitSignal(pdf_handler.pdf_import_status):
            pdf_handler.import_pdf(
                pdf_path="/path/to/document.pdf",
                workspace_id="workspace_1",
                session_id="session_1",
            )

        # Verify conversion was started
        pdf_handler._docling_service.convert_pdf.assert_called_once_with(
            "/path/to/document.pdf"
        )

        # Verify state was set
        assert pdf_handler._pending_pdf_path == "/path/to/document.pdf"
        assert pdf_handler._current_workspace_id == "workspace_1"
        assert pdf_handler._current_session_id == "session_1"

    def test_import_pdf_when_busy(self, pdf_handler, qtbot):
        """Test PDF import when DoclingService is busy."""
        pdf_handler._docling_service.is_busy = Mock(return_value=True)
        pdf_handler._docling_service.convert_pdf = Mock()

        with qtbot.waitSignal(pdf_handler.error_occurred) as blocker:
            pdf_handler.import_pdf(
                pdf_path="/path/to/document.pdf",
                workspace_id="workspace_1",
                session_id="session_1",
            )

        # Verify error message
        assert "already in progress" in blocker.args[0]

        # Verify conversion was NOT started
        pdf_handler._docling_service.convert_pdf.assert_not_called()


class TestPdfConversionComplete:
    """Test _on_pdf_conversion_complete method."""

    @patch("ui.viewmodels.chat.pdf_handler.uuid4")
    def test_conversion_complete_success(
        self,
        mock_uuid4,
        pdf_handler,
        qtbot,
        mock_artifact_repository,
        mock_artifact_viewmodel,
        mock_rag_orchestrator,
        successful_conversion_result,
    ):
        """Test successful PDF conversion and artifact creation."""
        # Setup
        mock_uuid = UUID("12345678-1234-5678-1234-567812345678")
        mock_uuid4.return_value = mock_uuid
        mock_artifact_repository.get_collection.return_value = None

        # Set state as if import was initiated
        pdf_handler._pending_pdf_path = "/path/to/document.pdf"
        pdf_handler._current_workspace_id = "workspace_1"
        pdf_handler._current_session_id = "session_1"

        # Trigger conversion complete
        with qtbot.waitSignals(
            [pdf_handler.pdf_import_status, mock_artifact_viewmodel.set_artifact],
            timeout=1000,
        ):
            pdf_handler._on_pdf_conversion_complete(successful_conversion_result)

        # Verify artifact was created and saved
        mock_artifact_repository.save_collection.assert_called_once()
        call_args = mock_artifact_repository.save_collection.call_args
        assert call_args[0][0] == "session_1"  # session_id
        collection = call_args[0][1]
        assert isinstance(collection, ArtifactCollectionV1)
        assert len(collection.artifacts) == 1
        assert collection.artifacts[0].id == str(mock_uuid)

        # Verify artifact viewmodel was updated
        mock_artifact_viewmodel.set_artifact.assert_called_once()
        artifact = mock_artifact_viewmodel.set_artifact.call_args[0][0]
        assert isinstance(artifact, ArtifactV3)
        assert len(artifact.contents) == 1
        assert artifact.contents[0].title == "document.pdf"
        assert artifact.contents[0].full_markdown == successful_conversion_result.markdown

        # Verify RAG indexing was triggered
        mock_rag_orchestrator.index_pdf_artifact.assert_called_once()
        rag_call = mock_rag_orchestrator.index_pdf_artifact.call_args
        assert rag_call.kwargs["workspace_id"] == "workspace_1"
        assert rag_call.kwargs["session_id"] == "session_1"
        assert rag_call.kwargs["entry_id"] == str(mock_uuid)
        assert rag_call.kwargs["source_name"] == "document.pdf"
        assert rag_call.kwargs["content"] == successful_conversion_result.markdown
        assert rag_call.kwargs["source_path"] == "/path/to/document.pdf"

        # Verify state was cleaned up
        assert pdf_handler._pending_pdf_path is None
        assert pdf_handler._current_workspace_id is None
        assert pdf_handler._current_session_id is None

    @patch("ui.viewmodels.chat.pdf_handler.uuid4")
    def test_conversion_complete_appends_to_existing_collection(
        self,
        mock_uuid4,
        pdf_handler,
        mock_artifact_repository,
        successful_conversion_result,
    ):
        """Test that PDF artifact is appended to existing collection."""
        mock_uuid = UUID("12345678-1234-5678-1234-567812345678")
        mock_uuid4.return_value = mock_uuid

        # Create existing collection
        existing_entry = ArtifactEntry(
            id="existing_entry",
            artifact=ArtifactV3(currentIndex=1, contents=[]),
            export_meta=ArtifactExportMeta(),
        )
        existing_collection = ArtifactCollectionV1(
            version=1,
            artifacts=[existing_entry],
            active_artifact_id="existing_entry",
        )
        mock_artifact_repository.get_collection.return_value = existing_collection

        # Set state
        pdf_handler._current_workspace_id = "workspace_1"
        pdf_handler._current_session_id = "session_1"

        # Trigger conversion
        pdf_handler._on_pdf_conversion_complete(successful_conversion_result)

        # Verify artifact was appended
        call_args = mock_artifact_repository.save_collection.call_args
        collection = call_args[0][1]
        assert len(collection.artifacts) == 2
        assert collection.artifacts[0].id == "existing_entry"
        assert collection.artifacts[1].id == str(mock_uuid)
        assert collection.active_artifact_id == str(mock_uuid)

    def test_conversion_complete_failure(
        self, pdf_handler, qtbot, failed_conversion_result
    ):
        """Test handling of failed PDF conversion."""
        pdf_handler._pending_pdf_path = "/path/to/document.pdf"
        pdf_handler._current_workspace_id = "workspace_1"
        pdf_handler._current_session_id = "session_1"

        with qtbot.waitSignals(
            [pdf_handler.error_occurred, pdf_handler.pdf_import_status], timeout=1000
        ):
            pdf_handler._on_pdf_conversion_complete(failed_conversion_result)

        # Verify state was cleaned up
        assert pdf_handler._pending_pdf_path is None
        assert pdf_handler._current_workspace_id is None
        assert pdf_handler._current_session_id is None

    def test_conversion_complete_no_session(
        self, pdf_handler, qtbot, successful_conversion_result
    ):
        """Test conversion complete when no session is active."""
        # No session_id set
        pdf_handler._current_session_id = None

        with qtbot.waitSignals(
            [pdf_handler.error_occurred, pdf_handler.pdf_import_status], timeout=1000
        ):
            pdf_handler._on_pdf_conversion_complete(successful_conversion_result)

        # Verify state was cleaned up
        assert pdf_handler._pending_pdf_path is None


class TestIsBusy:
    """Test is_busy method."""

    def test_is_busy_when_converting(self, pdf_handler):
        """Test is_busy returns True when conversion is in progress."""
        pdf_handler._docling_service.is_busy = Mock(return_value=True)
        assert pdf_handler.is_busy() is True

    def test_is_busy_when_idle(self, pdf_handler):
        """Test is_busy returns False when no conversion is in progress."""
        pdf_handler._docling_service.is_busy = Mock(return_value=False)
        assert pdf_handler.is_busy() is False


class TestCleanupConversionState:
    """Test _cleanup_conversion_state method."""

    def test_cleanup_conversion_state(self, pdf_handler):
        """Test that cleanup properly resets all state."""
        # Set some state
        pdf_handler._pending_pdf_path = "/path/to/file.pdf"
        pdf_handler._current_workspace_id = "workspace_1"
        pdf_handler._current_session_id = "session_1"

        # Cleanup
        pdf_handler._cleanup_conversion_state()

        # Verify all state is None
        assert pdf_handler._pending_pdf_path is None
        assert pdf_handler._current_workspace_id is None
        assert pdf_handler._current_session_id is None
