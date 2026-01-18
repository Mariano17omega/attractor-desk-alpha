"""Unit tests for ArtifactViewModel."""

import pytest
from unittest.mock import MagicMock, Mock
from PySide6.QtCore import QObject

from ui.viewmodels.chat.artifact_viewmodel import ArtifactViewModel
from core.types import (
    ArtifactCollectionV1,
    ArtifactEntry,
    ArtifactExportMeta,
    ArtifactV3,
    ArtifactMarkdownV3,
    ArtifactCodeV3,
    ArtifactPdfV1,
)


@pytest.fixture
def mock_artifact_repository():
    """Create a mock ArtifactRepository."""
    return Mock()


@pytest.fixture
def artifact_viewmodel(mock_artifact_repository):
    """Create an ArtifactViewModel instance with mock repository."""
    return ArtifactViewModel(artifact_repository=mock_artifact_repository)


@pytest.fixture
def sample_text_artifact():
    """Create a sample text artifact with multiple versions."""
    return ArtifactV3(
        currentIndex=1,
        contents=[
            ArtifactMarkdownV3(
                index=1,
                type="text",
                title="Version 1",
                fullMarkdown="# Version 1 Content",
            ),
            ArtifactMarkdownV3(
                index=2,
                type="text",
                title="Version 2",
                fullMarkdown="# Version 2 Content",
            ),
            ArtifactMarkdownV3(
                index=3,
                type="text",
                title="Version 3",
                fullMarkdown="# Version 3 Content",
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
                title="test.py",
                code="print('Hello, World!')",
                language="python",
            ),
        ],
    )


@pytest.fixture
def sample_pdf_artifact():
    """Create a sample PDF artifact (ChatPDF mode)."""
    return ArtifactV3(
        currentIndex=1,
        contents=[
            ArtifactPdfV1(
                index=1,
                type="pdf",
                title="Document.pdf",
                pdfPath="/path/to/document.pdf",
                totalPages=10,
                currentPage=1,
                ragDocumentId="doc_123",
            ),
        ],
    )


@pytest.fixture
def sample_collection_with_text(sample_text_artifact):
    """Create a collection with a text artifact."""
    entry = ArtifactEntry(
        id="entry_1",
        artifact=sample_text_artifact,
        export_meta=ArtifactExportMeta(),
    )
    return ArtifactCollectionV1(
        version=1,
        artifacts=[entry],
        active_artifact_id="entry_1",
    )


@pytest.fixture
def sample_collection_with_pdf(sample_pdf_artifact):
    """Create a collection with a PDF artifact."""
    entry = ArtifactEntry(
        id="entry_pdf",
        artifact=sample_pdf_artifact,
        export_meta=ArtifactExportMeta(),
    )
    return ArtifactCollectionV1(
        version=1,
        artifacts=[entry],
        active_artifact_id="entry_pdf",
    )


class TestArtifactViewModelInitialization:
    """Test ArtifactViewModel initialization."""

    def test_initialization(self, artifact_viewmodel):
        """Test that ArtifactViewModel initializes with correct defaults."""
        assert artifact_viewmodel.current_artifact is None
        assert artifact_viewmodel.conversation_mode == "normal"
        assert artifact_viewmodel.active_pdf_document_id is None

    def test_is_qobject(self, artifact_viewmodel):
        """Test that ArtifactViewModel is a QObject."""
        assert isinstance(artifact_viewmodel, QObject)


class TestArtifactProperties:
    """Test artifact property accessors."""

    def test_current_artifact_property(self, artifact_viewmodel, sample_text_artifact):
        """Test current_artifact property getter."""
        artifact_viewmodel._artifact = sample_text_artifact
        assert artifact_viewmodel.current_artifact == sample_text_artifact

    def test_conversation_mode_property(self, artifact_viewmodel):
        """Test conversation_mode property getter."""
        artifact_viewmodel._conversation_mode = "chatpdf"
        assert artifact_viewmodel.conversation_mode == "chatpdf"

    def test_active_pdf_document_id_property(self, artifact_viewmodel):
        """Test active_pdf_document_id property getter."""
        artifact_viewmodel._active_pdf_document_id = "doc_456"
        assert artifact_viewmodel.active_pdf_document_id == "doc_456"


class TestSetArtifact:
    """Test set_artifact method."""

    def test_set_artifact_emits_signal(
        self, qtbot, artifact_viewmodel, sample_text_artifact
    ):
        """Test that set_artifact emits artifact_changed signal."""
        with qtbot.waitSignal(artifact_viewmodel.artifact_changed):
            artifact_viewmodel.set_artifact(sample_text_artifact)

        assert artifact_viewmodel.current_artifact == sample_text_artifact

    def test_set_artifact_none(self, qtbot, artifact_viewmodel, sample_text_artifact):
        """Test setting artifact to None."""
        # First set an artifact
        artifact_viewmodel._artifact = sample_text_artifact

        # Then clear it
        with qtbot.waitSignal(artifact_viewmodel.artifact_changed):
            artifact_viewmodel.set_artifact(None)

        assert artifact_viewmodel.current_artifact is None


class TestVersionNavigation:
    """Test artifact version navigation."""

    def test_next_artifact_version_increments_index(
        self, qtbot, artifact_viewmodel, sample_text_artifact
    ):
        """Test next_artifact_version increments the current index."""
        artifact_viewmodel._artifact = sample_text_artifact
        assert artifact_viewmodel.current_artifact.current_index == 1

        with qtbot.waitSignal(artifact_viewmodel.artifact_changed):
            artifact_viewmodel.next_artifact_version()

        assert artifact_viewmodel.current_artifact.current_index == 2

    def test_next_artifact_version_at_end(
        self, artifact_viewmodel, sample_text_artifact
    ):
        """Test next_artifact_version does nothing at last version."""
        artifact_viewmodel._artifact = sample_text_artifact
        artifact_viewmodel._artifact.current_index = 3  # Last version

        # Should not emit signal
        artifact_viewmodel.next_artifact_version()

        assert artifact_viewmodel.current_artifact.current_index == 3

    def test_prev_artifact_version_decrements_index(
        self, qtbot, artifact_viewmodel, sample_text_artifact
    ):
        """Test prev_artifact_version decrements the current index."""
        artifact_viewmodel._artifact = sample_text_artifact
        artifact_viewmodel._artifact.current_index = 2

        with qtbot.waitSignal(artifact_viewmodel.artifact_changed):
            artifact_viewmodel.prev_artifact_version()

        assert artifact_viewmodel.current_artifact.current_index == 1

    def test_prev_artifact_version_at_start(
        self, artifact_viewmodel, sample_text_artifact
    ):
        """Test prev_artifact_version does nothing at first version."""
        artifact_viewmodel._artifact = sample_text_artifact
        artifact_viewmodel._artifact.current_index = 1  # First version

        # Should not emit signal
        artifact_viewmodel.prev_artifact_version()

        assert artifact_viewmodel.current_artifact.current_index == 1

    def test_version_navigation_without_artifact(self, artifact_viewmodel):
        """Test version navigation does nothing when no artifact is loaded."""
        # Should not raise errors
        artifact_viewmodel.next_artifact_version()
        artifact_viewmodel.prev_artifact_version()

        assert artifact_viewmodel.current_artifact is None


class TestLoadArtifactForSession:
    """Test load_artifact_for_session method."""

    def test_load_artifact_with_text_artifact(
        self,
        qtbot,
        artifact_viewmodel,
        mock_artifact_repository,
        sample_collection_with_text,
    ):
        """Test loading a text artifact from repository."""
        mock_artifact_repository.get_collection.return_value = sample_collection_with_text

        with qtbot.waitSignal(artifact_viewmodel.artifact_changed):
            artifact_viewmodel.load_artifact_for_session("session_1")

        mock_artifact_repository.get_collection.assert_called_once_with("session_1")
        assert artifact_viewmodel.current_artifact is not None
        assert artifact_viewmodel.conversation_mode == "normal"
        assert artifact_viewmodel.active_pdf_document_id is None

    def test_load_artifact_with_pdf_artifact(
        self,
        qtbot,
        artifact_viewmodel,
        mock_artifact_repository,
        sample_collection_with_pdf,
    ):
        """Test loading a PDF artifact sets ChatPDF mode."""
        mock_artifact_repository.get_collection.return_value = sample_collection_with_pdf

        with qtbot.waitSignal(artifact_viewmodel.artifact_changed):
            artifact_viewmodel.load_artifact_for_session("session_pdf")

        assert artifact_viewmodel.conversation_mode == "chatpdf"
        assert artifact_viewmodel.active_pdf_document_id == "doc_123"

    def test_load_artifact_with_no_collection(
        self, qtbot, artifact_viewmodel, mock_artifact_repository
    ):
        """Test loading artifact when no collection exists."""
        mock_artifact_repository.get_collection.return_value = None

        with qtbot.waitSignal(artifact_viewmodel.artifact_changed):
            artifact_viewmodel.load_artifact_for_session("nonexistent_session")

        assert artifact_viewmodel.current_artifact is None
        assert artifact_viewmodel.conversation_mode == "normal"
        assert artifact_viewmodel.active_pdf_document_id is None


class TestClearArtifact:
    """Test clear_artifact method."""

    def test_clear_artifact_resets_state(
        self, qtbot, artifact_viewmodel, sample_text_artifact
    ):
        """Test that clear_artifact resets all artifact state."""
        # Set up initial state
        artifact_viewmodel._artifact = sample_text_artifact
        artifact_viewmodel._conversation_mode = "chatpdf"
        artifact_viewmodel._active_pdf_document_id = "doc_999"

        # Clear artifact
        with qtbot.waitSignal(artifact_viewmodel.artifact_changed):
            artifact_viewmodel.clear_artifact()

        assert artifact_viewmodel.current_artifact is None
        assert artifact_viewmodel.conversation_mode == "normal"
        assert artifact_viewmodel.active_pdf_document_id is None


class TestArtifactSelection:
    """Test on_artifact_selected method."""

    def test_select_text_artifact(
        self,
        artifact_viewmodel,
        mock_artifact_repository,
        sample_collection_with_text,
    ):
        """Test selecting a text artifact updates conversation mode."""
        mock_artifact_repository.get_collection.return_value = sample_collection_with_text

        artifact_viewmodel.on_artifact_selected("entry_1", "session_1")

        assert artifact_viewmodel.conversation_mode == "normal"
        assert artifact_viewmodel.active_pdf_document_id is None

    def test_select_pdf_artifact(
        self,
        artifact_viewmodel,
        mock_artifact_repository,
        sample_collection_with_pdf,
    ):
        """Test selecting a PDF artifact updates conversation mode to ChatPDF."""
        mock_artifact_repository.get_collection.return_value = sample_collection_with_pdf

        artifact_viewmodel.on_artifact_selected("entry_pdf", "session_pdf")

        assert artifact_viewmodel.conversation_mode == "chatpdf"
        assert artifact_viewmodel.active_pdf_document_id == "doc_123"

    def test_select_nonexistent_artifact(
        self,
        artifact_viewmodel,
        mock_artifact_repository,
        sample_collection_with_text,
    ):
        """Test selecting non-existent artifact does nothing."""
        mock_artifact_repository.get_collection.return_value = sample_collection_with_text
        artifact_viewmodel._conversation_mode = "normal"

        artifact_viewmodel.on_artifact_selected("nonexistent_id", "session_1")

        # Mode should not change
        assert artifact_viewmodel.conversation_mode == "normal"

    def test_select_artifact_with_no_collection(
        self, artifact_viewmodel, mock_artifact_repository
    ):
        """Test selecting artifact when no collection exists."""
        mock_artifact_repository.get_collection.return_value = None

        # Should not raise errors
        artifact_viewmodel.on_artifact_selected("any_id", "any_session")


class TestConversationModeFromCollection:
    """Test _update_conversation_mode_from_collection method."""

    def test_update_mode_with_text_artifact(
        self, artifact_viewmodel, sample_collection_with_text
    ):
        """Test conversation mode is 'normal' for text artifacts."""
        artifact_viewmodel._update_conversation_mode_from_collection(
            sample_collection_with_text
        )

        assert artifact_viewmodel.conversation_mode == "normal"
        assert artifact_viewmodel.active_pdf_document_id is None

    def test_update_mode_with_pdf_artifact(
        self, artifact_viewmodel, sample_collection_with_pdf
    ):
        """Test conversation mode is 'chatpdf' for PDF artifacts."""
        artifact_viewmodel._update_conversation_mode_from_collection(
            sample_collection_with_pdf
        )

        assert artifact_viewmodel.conversation_mode == "chatpdf"
        assert artifact_viewmodel.active_pdf_document_id == "doc_123"

    def test_update_mode_with_none_collection(self, artifact_viewmodel):
        """Test conversation mode resets to 'normal' when collection is None."""
        artifact_viewmodel._conversation_mode = "chatpdf"
        artifact_viewmodel._active_pdf_document_id = "doc_old"

        artifact_viewmodel._update_conversation_mode_from_collection(None)

        assert artifact_viewmodel.conversation_mode == "normal"
        assert artifact_viewmodel.active_pdf_document_id is None

    def test_update_mode_with_empty_collection(self, artifact_viewmodel):
        """Test conversation mode resets when collection has no active entry."""
        empty_collection = ArtifactCollectionV1(
            version=1,
            artifacts=[],
            active_artifact_id=None,
        )

        artifact_viewmodel._update_conversation_mode_from_collection(empty_collection)

        assert artifact_viewmodel.conversation_mode == "normal"
        assert artifact_viewmodel.active_pdf_document_id is None
