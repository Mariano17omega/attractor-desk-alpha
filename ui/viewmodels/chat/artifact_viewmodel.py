"""ArtifactViewModel - Manages artifact state and versioning."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal

from core.persistence import ArtifactRepository
from core.types import ArtifactCollectionV1, ArtifactEntry, ArtifactV3


class ArtifactViewModel(QObject):
    """
    Manages artifact state, versioning, and selection.

    Responsibilities:
    - Track current artifact
    - Navigate artifact versions (prev/next)
    - Handle artifact selection
    - Determine conversation mode from artifact type
    """

    artifact_changed = Signal()

    def __init__(
        self,
        artifact_repository: ArtifactRepository,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._artifact_repository = artifact_repository
        self._artifact: Optional[ArtifactV3] = None
        self._conversation_mode: str = "normal"
        self._active_pdf_document_id: Optional[str] = None

    @property
    def current_artifact(self) -> Optional[ArtifactV3]:
        """Get the current artifact."""
        return self._artifact

    @property
    def conversation_mode(self) -> str:
        """Get the current conversation mode ('normal' or 'chatpdf')."""
        return self._conversation_mode

    @property
    def active_pdf_document_id(self) -> Optional[str]:
        """Get the active PDF document ID (for ChatPDF mode)."""
        return self._active_pdf_document_id

    def set_artifact(self, artifact: Optional[ArtifactV3]) -> None:
        """
        Set the current artifact.

        Args:
            artifact: The artifact to set as current
        """
        self._artifact = artifact
        self.artifact_changed.emit()

    def prev_artifact_version(self) -> None:
        """Navigate to the previous artifact version."""
        if not self._artifact:
            return

        if self._artifact.current_index > 1:
            self._artifact.current_index -= 1
            self.artifact_changed.emit()

    def next_artifact_version(self) -> None:
        """Navigate to the next artifact version."""
        if not self._artifact:
            return

        if self._artifact.current_index < len(self._artifact.contents):
            self._artifact.current_index += 1
            self.artifact_changed.emit()

    def load_artifact_for_session(self, session_id: str) -> None:
        """
        Load the artifact for a given session.

        Args:
            session_id: The session ID to load artifact for
        """
        collection = self._artifact_repository.get_collection(session_id)
        self._artifact = collection.get_active_artifact() if collection else None
        self._update_conversation_mode_from_collection(collection)
        self.artifact_changed.emit()

    def clear_artifact(self) -> None:
        """Clear the current artifact and reset conversation mode."""
        self._artifact = None
        self._conversation_mode = "normal"
        self._active_pdf_document_id = None
        self.artifact_changed.emit()

    def on_artifact_selected(self, artifact_id: str, session_id: str) -> None:
        """
        Handle artifact selection (e.g., switching between tabs).

        Args:
            artifact_id: The ID of the selected artifact
            session_id: The current session ID
        """
        collection = self._artifact_repository.get_collection(session_id)
        if not collection:
            return

        for entry in collection.artifacts:
            if entry.id != artifact_id:
                continue
            if entry.artifact.contents:
                current_content = entry.artifact.contents[-1]
                if current_content.type == "pdf":
                    self._conversation_mode = "chatpdf"
                    self._active_pdf_document_id = getattr(
                        current_content, "rag_document_id", None
                    )
                else:
                    self._conversation_mode = "normal"
                    self._active_pdf_document_id = None
            break

    def _update_conversation_mode_from_collection(
        self, collection: Optional[ArtifactCollectionV1]
    ) -> None:
        """
        Update conversation mode based on active artifact in collection.

        Args:
            collection: The artifact collection to inspect
        """
        if not collection:
            self._conversation_mode = "normal"
            self._active_pdf_document_id = None
            return

        active_entry = collection.get_active_entry()
        if not active_entry or not active_entry.artifact.contents:
            self._conversation_mode = "normal"
            self._active_pdf_document_id = None
            return

        current_content = active_entry.artifact.contents[-1]
        if current_content.type == "pdf":
            self._conversation_mode = "chatpdf"
            self._active_pdf_document_id = getattr(
                current_content, "rag_document_id", None
            )
        else:
            self._conversation_mode = "normal"
            self._active_pdf_document_id = None

    # ========== Public Facade Methods for Artifact Collection Operations ==========

    def get_collection(self, session_id: str) -> Optional[ArtifactCollectionV1]:
        """
        Get the artifact collection for a session.

        Args:
            session_id: The session ID

        Returns:
            The artifact collection or None if not found
        """
        return self._artifact_repository.get_collection(session_id)

    def save_collection(
        self, session_id: str, collection: ArtifactCollectionV1
    ) -> None:
        """
        Save an artifact collection.

        Args:
            session_id: The session ID
            collection: The collection to save
        """
        self._artifact_repository.save_collection(session_id, collection)
        self._artifact = collection.get_active_artifact()
        self.artifact_changed.emit()

    def create_artifact(self, session_id: str, entry: ArtifactEntry) -> None:
        """
        Create a new artifact and add it to the collection.

        Args:
            session_id: The session ID
            entry: The artifact entry to add
        """
        collection = self._artifact_repository.get_collection(session_id)
        if collection is None:
            collection = ArtifactCollectionV1(
                version=1,
                artifacts=[entry],
                active_artifact_id=entry.id,
            )
        else:
            collection.artifacts.append(entry)
            collection.active_artifact_id = entry.id

        self._artifact_repository.save_collection(session_id, collection)
        self._artifact = entry.artifact
        self.artifact_changed.emit()

    def select_artifact(self, session_id: str, artifact_id: str) -> bool:
        """
        Select an artifact by ID.

        Args:
            session_id: The session ID
            artifact_id: The artifact ID to select

        Returns:
            True if selection was successful, False otherwise
        """
        collection = self._artifact_repository.get_collection(session_id)
        if collection is None:
            return False

        if not collection.set_active_artifact(artifact_id):
            return False

        self._artifact_repository.save_collection(session_id, collection)
        self._artifact = collection.get_active_artifact()
        self._update_conversation_mode_from_collection(collection)
        return True

    def delete_artifact(self, session_id: str, artifact_id: str) -> None:
        """
        Delete an artifact from the collection.

        Args:
            session_id: The session ID
            artifact_id: The artifact ID to delete
        """
        collection = self._artifact_repository.get_collection(session_id)
        if collection is None:
            return

        # Remove artifact from collection
        collection.artifacts = [
            e for e in collection.artifacts if e.id != artifact_id
        ]

        # Select next artifact or clear
        if collection.artifacts:
            collection.active_artifact_id = collection.artifacts[0].id
            self._artifact = collection.get_active_artifact()
        else:
            collection.active_artifact_id = None
            self._artifact = None

        self._artifact_repository.save_collection(session_id, collection)
        self.artifact_changed.emit()

    def update_collection(
        self, session_id: str, collection: ArtifactCollectionV1
    ) -> None:
        """
        Update an artifact collection without changing the current artifact selection.

        Use this for content edits, title changes, page changes, etc.

        Args:
            session_id: The session ID
            collection: The updated collection
        """
        self._artifact_repository.save_collection(session_id, collection)
        # Sync current artifact from collection
        active = collection.get_active_artifact()
        if active:
            self._artifact = active
