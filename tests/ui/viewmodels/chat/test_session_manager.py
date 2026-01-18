"""Unit tests for SessionManager."""

import pytest
from unittest.mock import Mock
from langchain_core.messages import HumanMessage, AIMessage

from ui.viewmodels.chat.session_manager import SessionManager
from core.models import Session, Message, MessageRole


@pytest.fixture
def mock_session_repository():
    """Create a mock SessionRepository."""
    return Mock()


@pytest.fixture
def mock_message_repository():
    """Create a mock MessageRepository."""
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
def session_manager(mock_session_repository, mock_message_repository):
    """Create a SessionManager instance with mocked dependencies."""
    return SessionManager(
        session_repository=mock_session_repository,
        message_repository=mock_message_repository,
    )


class TestSessionManagerInitialization:
    """Test SessionManager initialization."""

    def test_initialization(self, session_manager):
        """Test that SessionManager initializes correctly."""
        assert session_manager._session_repository is not None
        assert session_manager._message_repository is not None
        assert session_manager._current_session is None
        assert session_manager._messages == []

    def test_initial_properties(self, session_manager):
        """Test initial property values."""
        assert session_manager.current_session is None
        assert session_manager.current_session_id is None
        assert session_manager.messages == []


class TestLoadSession:
    """Test load_session method."""

    def test_load_session_success(
        self,
        session_manager,
        mock_session_repository,
        mock_message_repository,
        mock_session,
        qtbot,
    ):
        """Test successful session loading."""
        # Setup mock messages
        user_msg = Mock(spec=Message)
        user_msg.role = MessageRole.USER
        user_msg.content = "Hello"

        ai_msg = Mock(spec=Message)
        ai_msg.role = MessageRole.ASSISTANT
        ai_msg.content = "Hi there!"

        mock_session_repository.get_by_id.return_value = mock_session
        mock_message_repository.get_by_session.return_value = [user_msg, ai_msg]

        with qtbot.waitSignal(session_manager.messages_loaded, timeout=1000) as blocker:
            session_manager.load_session("session_123")

        # Verify session was loaded
        assert session_manager.current_session == mock_session
        assert session_manager.current_session_id == "session_123"

        # Verify messages were converted
        assert len(session_manager.messages) == 2
        assert isinstance(session_manager.messages[0], HumanMessage)
        assert isinstance(session_manager.messages[1], AIMessage)
        assert session_manager.messages[0].content == "Hello"
        assert session_manager.messages[1].content == "Hi there!"

        # Verify signal was emitted with correct data
        emitted_messages = blocker.args[0]
        assert len(emitted_messages) == 2
        assert emitted_messages[0]["content"] == "Hello"
        assert emitted_messages[0]["is_user"] is True
        assert emitted_messages[1]["content"] == "Hi there!"
        assert emitted_messages[1]["is_user"] is False

    def test_load_session_not_found(
        self, session_manager, mock_session_repository, qtbot
    ):
        """Test loading a session that doesn't exist."""
        mock_session_repository.get_by_id.return_value = None

        # Should not emit signal when session not found
        session_manager.load_session("nonexistent")

        # Verify session wasn't loaded
        assert session_manager.current_session is None
        assert session_manager.current_session_id is None

    def test_load_session_empty_messages(
        self,
        session_manager,
        mock_session_repository,
        mock_message_repository,
        mock_session,
        qtbot,
    ):
        """Test loading a session with no messages."""
        mock_session_repository.get_by_id.return_value = mock_session
        mock_message_repository.get_by_session.return_value = []

        with qtbot.waitSignal(session_manager.messages_loaded, timeout=1000) as blocker:
            session_manager.load_session("session_123")

        assert session_manager.current_session == mock_session
        assert len(session_manager.messages) == 0
        assert blocker.args[0] == []


class TestClear:
    """Test clear method."""

    def test_clear_session(self, session_manager, mock_session, qtbot):
        """Test clearing session state."""
        # Setup initial state
        session_manager._current_session = mock_session
        session_manager._messages = [HumanMessage(content="Test")]

        with qtbot.waitSignal(session_manager.messages_loaded, timeout=1000) as blocker:
            session_manager.clear()

        # Verify state was cleared
        assert session_manager.current_session is None
        assert session_manager.current_session_id is None
        assert session_manager.messages == []

        # Verify signal was emitted with empty list
        assert blocker.args[0] == []

    def test_clear_empty_session(self, session_manager, qtbot):
        """Test clearing when already empty."""
        with qtbot.waitSignal(session_manager.messages_loaded, timeout=1000):
            session_manager.clear()

        assert session_manager.current_session is None
        assert session_manager.messages == []


class TestUpdateSessionTitle:
    """Test update_session_title method."""

    def test_update_title_success(
        self, session_manager, mock_session_repository, mock_session, qtbot
    ):
        """Test successful title update."""
        session_manager._current_session = mock_session

        with qtbot.waitSignal(session_manager.session_updated, timeout=1000):
            session_manager.update_session_title("New Title")

        # Verify title was updated
        assert mock_session.title == "New Title"
        mock_session_repository.update.assert_called_once_with(mock_session)

    def test_update_title_same_title(
        self, session_manager, mock_session_repository, mock_session
    ):
        """Test updating to the same title (should not update)."""
        session_manager._current_session = mock_session
        mock_session.title = "Same Title"

        session_manager.update_session_title("Same Title")

        # Verify no update was made
        mock_session_repository.update.assert_not_called()

    def test_update_title_no_session(self, session_manager, mock_session_repository):
        """Test updating title when no session is active."""
        session_manager.update_session_title("New Title")

        # Verify no update was attempted
        mock_session_repository.update.assert_not_called()


class TestSetCurrentSession:
    """Test set_current_session method."""

    def test_set_current_session(self, session_manager, mock_session):
        """Test setting current session."""
        session_manager.set_current_session(mock_session)

        assert session_manager.current_session == mock_session
        assert session_manager.current_session_id == "session_123"

    def test_set_current_session_none(self, session_manager):
        """Test setting current session to None."""
        session_manager.set_current_session(None)

        assert session_manager.current_session is None
        assert session_manager.current_session_id is None


class TestProperties:
    """Test property accessors."""

    def test_messages_property(self, session_manager):
        """Test messages property returns a list."""
        messages = [HumanMessage(content="Test")]
        session_manager._messages = messages

        assert session_manager.messages == messages

    def test_current_session_property(self, session_manager, mock_session):
        """Test current_session property."""
        session_manager._current_session = mock_session

        assert session_manager.current_session == mock_session

    def test_current_session_id_property(self, session_manager, mock_session):
        """Test current_session_id property."""
        session_manager._current_session = mock_session

        assert session_manager.current_session_id == "session_123"

    def test_current_session_id_none(self, session_manager):
        """Test current_session_id when no session is active."""
        assert session_manager.current_session_id is None
