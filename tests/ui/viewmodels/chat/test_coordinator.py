"""Integration tests for ChatCoordinator."""

import pytest
from unittest.mock import Mock, MagicMock

from ui.viewmodels.chat.coordinator import ChatCoordinator
from core.models import Session


@pytest.fixture
def mock_repositories():
    """Create mock repositories."""
    return {
        "message": Mock(),
        "attachment": Mock(),
        "artifact": Mock(),
        "session": Mock(),
    }


@pytest.fixture
def mock_settings_viewmodel():
    """Create a mock SettingsViewModel."""
    settings = Mock()
    settings.deep_search_enabled = False
    settings.default_model = "anthropic/claude-3.5-sonnet"
    settings.image_model = "anthropic/claude-3.5-sonnet"
    settings.api_key = "test_api_key"
    settings.rag_enabled = True
    settings.rag_scope = "global"
    settings.rag_k_lex = 10
    settings.rag_k_vec = 5
    settings.rag_rrf_k = 60
    settings.rag_max_candidates = 100
    settings.rag_embedding_model = "openai/text-embedding-3-small"
    settings.rag_enable_query_rewrite = True
    settings.rag_enable_llm_rerank = False
    settings.search_provider = "exa"
    settings.deep_search_num_results = 5
    settings.exa_api_key = None
    settings.firecrawl_api_key = None
    settings.rag_chunk_size_chars = 500
    settings.rag_chunk_overlap_chars = 50
    return settings


@pytest.fixture
def coordinator(mock_repositories, mock_settings_viewmodel):
    """Create a ChatCoordinator instance with mocked dependencies."""
    return ChatCoordinator(
        message_repository=mock_repositories["message"],
        attachment_repository=mock_repositories["attachment"],
        artifact_repository=mock_repositories["artifact"],
        session_repository=mock_repositories["session"],
        settings_viewmodel=mock_settings_viewmodel,
        rag_service=Mock(),
        local_rag_service=Mock(),
    )


class TestChatCoordinatorInitialization:
    """Test ChatCoordinator initialization."""

    def test_initialization(self, coordinator):
        """Test that ChatCoordinator initializes all subsystems."""
        assert coordinator.sessions is not None
        assert coordinator.artifacts is not None
        assert coordinator.rag is not None
        assert coordinator.pdf is not None
        assert coordinator.chatpdf is not None
        assert coordinator.graph is not None

    def test_subsystem_types(self, coordinator):
        """Test that subsystems are of correct types."""
        from ui.viewmodels.chat.session_manager import SessionManager
        from ui.viewmodels.chat.artifact_viewmodel import ArtifactViewModel
        from ui.viewmodels.chat.rag_orchestrator import RagOrchestrator
        from ui.viewmodels.chat.pdf_handler import PdfHandler
        from ui.viewmodels.chat.chatpdf_service import ChatPdfService
        from ui.viewmodels.chat.graph_execution_handler import GraphExecutionHandler

        assert isinstance(coordinator.sessions, SessionManager)
        assert isinstance(coordinator.artifacts, ArtifactViewModel)
        assert isinstance(coordinator.rag, RagOrchestrator)
        assert isinstance(coordinator.pdf, PdfHandler)
        assert isinstance(coordinator.chatpdf, ChatPdfService)
        assert isinstance(coordinator.graph, GraphExecutionHandler)


class TestSignalForwarding:
    """Test signal forwarding from subsystems."""

    def test_messages_loaded_signal(self, coordinator, qtbot):
        """Test that messages_loaded signal is forwarded."""
        with qtbot.waitSignal(coordinator.messages_loaded, timeout=1000):
            coordinator.sessions.messages_loaded.emit([])

    def test_artifact_changed_signal(self, coordinator, qtbot):
        """Test that artifact_changed signal is forwarded."""
        with qtbot.waitSignal(coordinator.artifact_changed, timeout=1000):
            coordinator.artifacts.artifact_changed.emit()

    def test_error_occurred_signal(self, coordinator, qtbot):
        """Test that error_occurred signal is forwarded."""
        with qtbot.waitSignal(coordinator.error_occurred, timeout=1000):
            coordinator.pdf.error_occurred.emit("Test error")


class TestBackwardCompatibilityProperties:
    """Test backward compatibility properties."""

    def test_messages_property(self, coordinator):
        """Test messages property delegates to sessions."""
        assert coordinator.messages == coordinator.sessions.messages

    def test_current_artifact_property(self, coordinator):
        """Test current_artifact property delegates to artifacts."""
        assert coordinator.current_artifact == coordinator.artifacts.current_artifact

    def test_is_loading_property(self, coordinator):
        """Test is_loading property delegates to graph."""
        assert coordinator.is_loading == coordinator.graph.is_loading

    def test_current_session_id_property(self, coordinator):
        """Test current_session_id property delegates to sessions."""
        assert coordinator.current_session_id == coordinator.sessions.current_session_id


class TestLoadSession:
    """Test load_session integration."""

    def test_load_session_coordinates_subsystems(
        self, coordinator, mock_repositories, qtbot
    ):
        """Test that load_session coordinates all subsystems."""
        mock_session = Mock(spec=Session)
        mock_session.id = "session_123"
        mock_session.workspace_id = "workspace_456"

        mock_repositories["session"].get_by_id.return_value = mock_session
        mock_repositories["message"].get_by_session.return_value = []

        with qtbot.waitSignal(coordinator.messages_loaded, timeout=1000):
            coordinator.load_session("session_123")

        # Verify session was loaded
        mock_repositories["session"].get_by_id.assert_called_once_with("session_123")

        # Verify artifacts were loaded
        assert coordinator.artifacts._session_id == "session_123"


class TestClear:
    """Test clear integration."""

    def test_clear_coordinates_subsystems(self, coordinator, qtbot):
        """Test that clear coordinates all subsystems."""
        # Setup some state
        mock_session = Mock(spec=Session)
        mock_session.id = "session_123"
        coordinator.sessions._current_session = mock_session

        with qtbot.waitSignal(coordinator.messages_loaded, timeout=1000):
            coordinator.clear()

        # Verify session was cleared
        assert coordinator.sessions.current_session is None

        # Verify graph was cleared
        assert coordinator.graph._current_session is None


class TestSendMessage:
    """Test send_message integration."""

    def test_send_message_without_session(self, coordinator):
        """Test that send_message does nothing without a session."""
        coordinator.send_message("Test message")
        # Should not raise an error, just return early


class TestAttachmentManagement:
    """Test attachment management."""

    def test_add_pending_attachment(self, coordinator, qtbot, tmp_path):
        """Test adding a pending attachment."""
        # Create a temporary file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Setup session
        mock_session = Mock(spec=Session)
        mock_session.id = "session_123"
        coordinator.sessions._current_session = mock_session

        with qtbot.waitSignal(coordinator.pending_attachments_changed, timeout=1000):
            coordinator.add_pending_attachment(str(test_file))

        assert len(coordinator.pending_attachments) == 1
        assert str(test_file) in coordinator.pending_attachments

    def test_add_pending_attachment_no_session(self, coordinator, qtbot):
        """Test adding attachment without session emits error."""
        with qtbot.waitSignal(coordinator.error_occurred, timeout=1000):
            coordinator.add_pending_attachment("/path/to/file.txt")


class TestArtifactNavigation:
    """Test artifact navigation methods."""

    def test_prev_artifact_version(self, coordinator):
        """Test navigating to previous artifact version."""
        # Just verify it delegates correctly
        coordinator.prev_artifact_version()
        # Should not raise an error

    def test_next_artifact_version(self, coordinator):
        """Test navigating to next artifact version."""
        # Just verify it delegates correctly
        coordinator.next_artifact_version()
        # Should not raise an error


class TestPDFMethods:
    """Test PDF-related methods."""

    def test_import_pdf_without_session(self, coordinator, qtbot):
        """Test importing PDF without session emits error."""
        with qtbot.waitSignal(coordinator.error_occurred, timeout=1000):
            coordinator.import_pdf("/path/to/file.pdf")

    def test_open_chatpdf_without_session(self, coordinator, qtbot):
        """Test opening ChatPDF without session emits error."""
        with qtbot.waitSignal(coordinator.error_occurred, timeout=1000):
            coordinator.open_chatpdf("/path/to/file.pdf")
