"""SessionManager - Manages session lifecycle and message state."""

import logging
from typing import Optional

from PySide6.QtCore import QObject, Signal
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from core.models import MessageRole, Session
from core.persistence import MessageRepository, SessionRepository

logger = logging.getLogger(__name__)


class SessionManager(QObject):
    """Manages session lifecycle, loading, and clearing.

    This class handles:
    - Loading sessions and their messages
    - Converting stored messages to LangChain format
    - Clearing sessions
    - Managing current session state

    Signals:
        messages_loaded(object): Emitted when messages are loaded (list of message dicts)
        session_updated(): Emitted when session is updated
    """

    messages_loaded = Signal(object)
    session_updated = Signal()

    def __init__(
        self,
        session_repository: SessionRepository,
        message_repository: MessageRepository,
        parent: Optional[QObject] = None,
    ):
        """Initialize the session manager.

        Args:
            session_repository: Repository for session persistence
            message_repository: Repository for message persistence
            parent: Optional parent QObject
        """
        super().__init__(parent)
        self._session_repository = session_repository
        self._message_repository = message_repository

        self._current_session: Optional[Session] = None
        self._messages: list[BaseMessage] = []

    @property
    def current_session(self) -> Optional[Session]:
        """Get the current session."""
        return self._current_session

    @property
    def current_session_id(self) -> Optional[str]:
        """Get the current session ID."""
        return self._current_session.id if self._current_session else None

    @property
    def messages(self) -> list[BaseMessage]:
        """Get the current message list."""
        return self._messages

    def load_session(self, session_id: str) -> None:
        """Load a session and its messages.

        Args:
            session_id: The ID of the session to load
        """
        session = self._session_repository.get_by_id(session_id)
        if session is None:
            logger.warning(f"Session {session_id} not found")
            return

        self._current_session = session
        stored_messages = self._message_repository.get_by_session(session_id)

        # Convert stored messages to LangChain format
        messages = []
        for message in stored_messages:
            if message.role == MessageRole.USER:
                messages.append(HumanMessage(content=message.content))
            elif message.role == MessageRole.ASSISTANT:
                messages.append(AIMessage(content=message.content))

        self._messages = messages

        # Emit loaded messages for UI
        self.messages_loaded.emit(
            [
                {"content": msg.content, "is_user": isinstance(msg, HumanMessage)}
                for msg in messages
            ]
        )

    def clear(self) -> None:
        """Clear the current session and messages."""
        self._current_session = None
        self._messages = []
        self.messages_loaded.emit([])

    def update_session_title(self, title: str) -> None:
        """Update the current session's title.

        Args:
            title: The new title for the session
        """
        if not self._current_session:
            logger.warning("Cannot update title: no active session")
            return

        if self._current_session.title != title:
            self._current_session.title = title
            self._session_repository.update(self._current_session)
            self.session_updated.emit()

    def set_current_session(self, session: Optional[Session]) -> None:
        """Set the current session.

        Args:
            session: The session to set as current
        """
        self._current_session = session
