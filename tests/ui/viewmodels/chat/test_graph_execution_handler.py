"""Unit tests for GraphExecutionHandler."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage

from ui.viewmodels.chat.graph_execution_handler import GraphExecutionHandler
from core.models import Session, Message, MessageRole


@pytest.fixture
def mock_message_repository():
    """Create a mock MessageRepository."""
    return Mock()


@pytest.fixture
def mock_attachment_repository():
    """Create a mock MessageAttachmentRepository."""
    return Mock()


@pytest.fixture
def mock_artifact_repository():
    """Create a mock ArtifactRepository."""
    return Mock()


@pytest.fixture
def mock_session_repository():
    """Create a mock SessionRepository."""
    return Mock()


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
    return settings


@pytest.fixture
def mock_artifact_viewmodel():
    """Create a mock ArtifactViewModel."""
    viewmodel = Mock()
    viewmodel.conversation_mode = "normal"
    viewmodel.active_pdf_document_id = None
    viewmodel.current_artifact = None
    return viewmodel


@pytest.fixture
def mock_rag_orchestrator():
    """Create a mock RagOrchestrator."""
    return Mock()


@pytest.fixture
def mock_session():
    """Create a mock Session."""
    session = Mock(spec=Session)
    session.id = "session_123"
    session.workspace_id = "workspace_456"
    session.title = "Test Session"
    session.updated_at = None
    return session


@pytest.fixture
def graph_handler(
    mock_message_repository,
    mock_attachment_repository,
    mock_artifact_repository,
    mock_session_repository,
    mock_settings_viewmodel,
    mock_artifact_viewmodel,
    mock_rag_orchestrator,
):
    """Create a GraphExecutionHandler instance with mocked dependencies."""
    return GraphExecutionHandler(
        message_repository=mock_message_repository,
        attachment_repository=mock_attachment_repository,
        artifact_repository=mock_artifact_repository,
        session_repository=mock_session_repository,
        settings_viewmodel=mock_settings_viewmodel,
        artifact_viewmodel=mock_artifact_viewmodel,
        rag_orchestrator=mock_rag_orchestrator,
    )


class TestGraphExecutionHandlerInitialization:
    """Test GraphExecutionHandler initialization."""

    def test_initialization(self, graph_handler):
        """Test that GraphExecutionHandler initializes correctly."""
        assert graph_handler._message_repository is not None
        assert graph_handler._attachment_repository is not None
        assert graph_handler._artifact_repository is not None
        assert graph_handler._session_repository is not None
        assert graph_handler._settings_viewmodel is not None
        assert graph_handler._artifact_viewmodel is not None
        assert graph_handler._rag_orchestrator is not None
        assert graph_handler._messages == []
        assert graph_handler._internal_messages == []
        assert graph_handler._is_loading is False
        assert graph_handler._current_session is None
        assert graph_handler._worker is None
        assert graph_handler._active_run_token is None

    def test_initial_loading_state(self, graph_handler):
        """Test initial loading state is False."""
        assert graph_handler.is_loading is False


class TestSessionManagement:
    """Test session management methods."""

    def test_set_session(self, graph_handler, mock_session):
        """Test setting the current session."""
        graph_handler.set_session(mock_session)
        assert graph_handler._current_session == mock_session

    def test_set_messages(self, graph_handler):
        """Test setting messages."""
        messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
        ]
        graph_handler.set_messages(messages)
        assert graph_handler._messages == messages
        assert graph_handler._internal_messages == messages

    def test_set_pending_attachments(self, graph_handler):
        """Test setting pending attachments."""
        attachments = ["/path/to/image1.png", "/path/to/image2.png"]
        graph_handler.set_pending_attachments(attachments)
        assert graph_handler._pending_attachments == attachments


class TestSendMessage:
    """Test send_message method."""

    @patch("ui.viewmodels.chat.graph_execution_handler.GraphWorker")
    @patch("ui.viewmodels.chat.graph_execution_handler.Message")
    def test_send_message_basic(
        self,
        mock_message_class,
        mock_graph_worker_class,
        graph_handler,
        mock_session,
        mock_message_repository,
        qtbot,
    ):
        """Test basic message sending."""
        # Setup
        graph_handler.set_session(mock_session)
        mock_user_message = Mock()
        mock_user_message.id = "msg_123"
        mock_message_class.create.return_value = mock_user_message

        # Mock the worker
        mock_worker = Mock()
        mock_graph_worker_class.return_value = mock_worker

        # Send message
        with qtbot.waitSignals(
            [graph_handler.message_added, graph_handler.is_loading_changed],
            timeout=1000,
        ):
            graph_handler.send_message("Hello, world!")

        # Verify message was saved
        mock_message_class.create.assert_called_once_with(
            session_id="session_123",
            role=MessageRole.USER,
            content="Hello, world!",
        )
        mock_message_repository.add.assert_called_once_with(mock_user_message)

        # Verify loading state changed
        assert graph_handler.is_loading is True

        # Verify worker was started
        mock_worker.start.assert_called_once()

    def test_send_message_without_session(self, graph_handler):
        """Test sending message without active session."""
        # Should do nothing if no session is set
        graph_handler.send_message("Hello")
        # Verify no messages were added
        assert len(graph_handler._messages) == 0

    @patch("ui.viewmodels.chat.graph_execution_handler.GraphWorker")
    @patch("ui.viewmodels.chat.graph_execution_handler.Message")
    def test_send_message_when_loading(
        self,
        mock_message_class,
        mock_graph_worker_class,
        graph_handler,
        mock_session,
    ):
        """Test that sending message while loading is ignored."""
        graph_handler.set_session(mock_session)
        graph_handler._is_loading = True

        graph_handler.send_message("Hello")

        # Verify no message was created
        mock_message_class.create.assert_not_called()


class TestCancelGeneration:
    """Test cancel_generation method."""

    def test_cancel_generation(self, graph_handler, qtbot):
        """Test canceling generation."""
        graph_handler._is_loading = True
        graph_handler._active_run_token = "some_token"

        with qtbot.waitSignals(
            [graph_handler.is_loading_changed, graph_handler.status_changed],
            timeout=1000,
        ):
            graph_handler.cancel_generation()

        assert graph_handler.is_loading is False
        assert graph_handler._active_run_token is None

    def test_cancel_generation_when_not_loading(self, graph_handler):
        """Test canceling when not loading does nothing."""
        graph_handler._is_loading = False
        graph_handler.cancel_generation()
        # Should complete without error
        assert graph_handler.is_loading is False


class TestGraphFinished:
    """Test _on_graph_finished method."""

    def test_graph_finished_with_messages(
        self,
        graph_handler,
        mock_session,
        mock_message_repository,
        qtbot,
    ):
        """Test handling successful graph execution with new messages."""
        graph_handler.set_session(mock_session)
        graph_handler._active_run_token = "test_token"
        graph_handler._active_session_id = mock_session.id  # Set session ID for race condition check
        graph_handler._is_loading = True

        # Create result with new AI message
        result = {
            "messages": [
                HumanMessage(content="Hello"),
                AIMessage(content="Hi there!"),
            ],
            "artifact": None,
        }

        with qtbot.waitSignals(
            [graph_handler.message_added, graph_handler.is_loading_changed],
            timeout=1000,
        ):
            graph_handler._on_graph_finished(result, "test_token")

        # Verify loading stopped
        assert graph_handler.is_loading is False

        # Verify message was saved (AI message)
        assert mock_message_repository.add.called

    def test_graph_finished_stale_token(self, graph_handler, qtbot):
        """Test that stale results are ignored."""
        graph_handler._active_run_token = "current_token"
        graph_handler._is_loading = True

        result = {
            "messages": [AIMessage(content="Stale response")],
        }

        # Should not emit any signals
        graph_handler._on_graph_finished(result, "old_token")

        # Verify loading state unchanged
        assert graph_handler.is_loading is True

    def test_graph_finished_with_artifact(
        self,
        graph_handler,
        mock_session,
        mock_artifact_viewmodel,
        mock_artifact_repository,
        mock_rag_orchestrator,
    ):
        """Test handling graph result with artifact."""
        graph_handler.set_session(mock_session)
        graph_handler._active_run_token = "test_token"
        graph_handler._active_session_id = mock_session.id

        mock_artifact = Mock()
        mock_artifact.contents = ["content1", "content2"]
        result = {
            "messages": [],
            "artifact": mock_artifact,
        }

        graph_handler._on_graph_finished(result, "test_token")

        # Verify artifact was set
        mock_artifact_viewmodel.set_artifact.assert_called_once_with(mock_artifact)

        # Verify artifact was saved
        mock_artifact_repository.save_for_session.assert_called_once_with(
            "session_123", mock_artifact
        )

        # Verify RAG indexing was triggered
        mock_rag_orchestrator.index_active_text_artifact.assert_called_once()


class TestGraphError:
    """Test _on_graph_error method."""

    def test_graph_error(self, graph_handler, qtbot):
        """Test handling graph execution error."""
        graph_handler._active_run_token = "test_token"
        graph_handler._is_loading = True

        with qtbot.waitSignal(graph_handler.error_occurred, timeout=1000) as blocker:
            graph_handler._on_graph_error("Test error", "test_token")

        assert blocker.args[0] == "Test error"
        assert graph_handler.is_loading is False

    def test_graph_error_stale_token(self, graph_handler):
        """Test that stale errors are ignored."""
        graph_handler._active_run_token = "current_token"
        graph_handler._is_loading = True

        graph_handler._on_graph_error("Stale error", "old_token")

        # Verify loading state unchanged
        assert graph_handler.is_loading is True


class TestPrepareGraphState:
    """Test _prepare_graph_state method."""

    def test_prepare_graph_state_basic(
        self, graph_handler, mock_settings_viewmodel, mock_artifact_viewmodel
    ):
        """Test preparing basic graph state."""
        messages = [HumanMessage(content="Hello")]
        graph_handler.set_messages(messages)

        state = graph_handler._prepare_graph_state()

        assert "messages" in state
        assert "internal_messages" in state
        assert "web_search_enabled" in state
        assert "conversation_mode" in state
        assert "active_pdf_document_id" in state
        assert state["messages"] == messages
        assert state["web_search_enabled"] is False
        assert state["conversation_mode"] == "normal"

    def test_prepare_graph_state_with_artifact(
        self, graph_handler, mock_artifact_viewmodel
    ):
        """Test preparing state with current artifact."""
        mock_artifact = Mock()
        mock_artifact_viewmodel.current_artifact = mock_artifact

        state = graph_handler._prepare_graph_state()

        assert "artifact" in state
        assert state["artifact"] == mock_artifact


class TestPrepareGraphConfig:
    """Test _prepare_graph_config method."""

    def test_prepare_graph_config(self, graph_handler, mock_session):
        """Test preparing graph configuration."""
        graph_handler.set_session(mock_session)

        config = graph_handler._prepare_graph_config()

        assert "configurable" in config
        configurable = config["configurable"]
        assert "assistant_id" in configurable
        assert "model" in configurable
        assert "session_id" in configurable
        assert "workspace_id" in configurable
        assert configurable["session_id"] == "session_123"
        assert configurable["workspace_id"] == "workspace_456"
        assert configurable["model"] == "anthropic/claude-3.5-sonnet"
        assert configurable["rag_enabled"] is True
