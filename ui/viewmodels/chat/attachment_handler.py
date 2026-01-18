"""AttachmentHandler - Manages pending file attachments for multimodal input."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal


class AttachmentHandler(QObject):
    """
    Manages pending file attachments (images) for multimodal LLM input.

    Handles validation, storage, and clearing of attachment paths that will
    be converted to data URLs when messages are sent.
    """

    pending_attachments_changed = Signal(object)  # list[str]

    def __init__(
        self,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._pending_attachments: list[str] = []

    @property
    def pending_attachments(self) -> list[str]:
        """Get copy of pending attachment file paths."""
        return self._pending_attachments.copy()

    def add_pending_attachment(self, file_path: str, session_active: bool = True) -> bool:
        """
        Add a file path to pending attachments.

        Args:
            file_path: Path to the attachment file
            session_active: Whether there's an active session (for validation)

        Returns:
            True if attachment added successfully, False otherwise
        """
        if not session_active:
            return False

        if not file_path:
            return False

        path = Path(file_path)
        if not path.exists():
            return False

        normalized = str(path)
        if normalized in self._pending_attachments:
            return False

        self._pending_attachments.append(normalized)
        self.pending_attachments_changed.emit(self._pending_attachments.copy())
        return True

    def clear_pending_attachments(self) -> None:
        """Clear all pending attachments."""
        if not self._pending_attachments:
            return

        self._pending_attachments = []
        self.pending_attachments_changed.emit(self._pending_attachments.copy())

    def has_attachments(self) -> bool:
        """Check if there are any pending attachments."""
        return len(self._pending_attachments) > 0

    def get_and_clear_attachments(self) -> list[str]:
        """
        Get pending attachments and clear the list (atomic operation).

        Returns:
            List of attachment file paths
        """
        attachments = self._pending_attachments.copy()
        if attachments:
            self._pending_attachments = []
            self.pending_attachments_changed.emit([])
        return attachments
