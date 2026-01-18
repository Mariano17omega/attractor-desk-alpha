"""Tests for AttachmentHandler."""

import pytest
from pathlib import Path
from PySide6.QtCore import QObject

from ui.viewmodels.chat.attachment_handler import AttachmentHandler


@pytest.fixture
def attachment_handler():
    """Create AttachmentHandler instance for testing."""
    return AttachmentHandler()


@pytest.fixture
def temp_image_file(tmp_path):
    """Create a temporary image file for testing."""
    image_file = tmp_path / "test_image.png"
    image_file.write_bytes(b"fake image data")
    return str(image_file)


def test_initial_state(attachment_handler):
    """Test initial state of AttachmentHandler."""
    assert attachment_handler.pending_attachments == []
    assert not attachment_handler.has_attachments()


def test_add_attachment_success(attachment_handler, temp_image_file, qtbot):
    """Test adding a valid attachment."""
    with qtbot.waitSignal(attachment_handler.pending_attachments_changed):
        result = attachment_handler.add_pending_attachment(temp_image_file, session_active=True)

    assert result is True
    assert len(attachment_handler.pending_attachments) == 1
    assert attachment_handler.has_attachments()
    assert temp_image_file in attachment_handler.pending_attachments


def test_add_attachment_no_session(attachment_handler, temp_image_file):
    """Test adding attachment when no session active."""
    result = attachment_handler.add_pending_attachment(temp_image_file, session_active=False)

    assert result is False
    assert len(attachment_handler.pending_attachments) == 0


def test_add_attachment_empty_path(attachment_handler):
    """Test adding empty file path."""
    result = attachment_handler.add_pending_attachment("", session_active=True)

    assert result is False
    assert len(attachment_handler.pending_attachments) == 0


def test_add_attachment_nonexistent_file(attachment_handler):
    """Test adding non-existent file."""
    result = attachment_handler.add_pending_attachment("/nonexistent/file.png", session_active=True)

    assert result is False
    assert len(attachment_handler.pending_attachments) == 0


def test_add_duplicate_attachment(attachment_handler, temp_image_file, qtbot):
    """Test adding same attachment twice."""
    # Add first time
    with qtbot.waitSignal(attachment_handler.pending_attachments_changed):
        result1 = attachment_handler.add_pending_attachment(temp_image_file, session_active=True)

    # Add second time (should be ignored)
    result2 = attachment_handler.add_pending_attachment(temp_image_file, session_active=True)

    assert result1 is True
    assert result2 is False
    assert len(attachment_handler.pending_attachments) == 1


def test_add_multiple_attachments(attachment_handler, tmp_path, qtbot):
    """Test adding multiple different attachments."""
    file1 = tmp_path / "image1.png"
    file2 = tmp_path / "image2.png"
    file1.write_bytes(b"image1")
    file2.write_bytes(b"image2")

    attachment_handler.add_pending_attachment(str(file1), session_active=True)
    attachment_handler.add_pending_attachment(str(file2), session_active=True)

    assert len(attachment_handler.pending_attachments) == 2
    assert str(file1) in attachment_handler.pending_attachments
    assert str(file2) in attachment_handler.pending_attachments


def test_clear_pending_attachments(attachment_handler, temp_image_file, qtbot):
    """Test clearing pending attachments."""
    # Add attachment
    attachment_handler.add_pending_attachment(temp_image_file, session_active=True)
    assert len(attachment_handler.pending_attachments) == 1

    # Clear attachments
    with qtbot.waitSignal(attachment_handler.pending_attachments_changed):
        attachment_handler.clear_pending_attachments()

    assert len(attachment_handler.pending_attachments) == 0
    assert not attachment_handler.has_attachments()


def test_clear_empty_attachments(attachment_handler):
    """Test clearing when already empty (should not emit signal)."""
    # Should not emit signal when clearing empty list
    attachment_handler.clear_pending_attachments()
    assert len(attachment_handler.pending_attachments) == 0


def test_get_and_clear_attachments(attachment_handler, temp_image_file, qtbot):
    """Test get and clear atomic operation."""
    # Add attachment
    attachment_handler.add_pending_attachment(temp_image_file, session_active=True)

    # Get and clear
    with qtbot.waitSignal(attachment_handler.pending_attachments_changed):
        attachments = attachment_handler.get_and_clear_attachments()

    assert len(attachments) == 1
    assert temp_image_file in attachments
    assert len(attachment_handler.pending_attachments) == 0
    assert not attachment_handler.has_attachments()


def test_get_and_clear_empty(attachment_handler):
    """Test get and clear when empty."""
    attachments = attachment_handler.get_and_clear_attachments()

    assert attachments == []
    assert len(attachment_handler.pending_attachments) == 0


def test_pending_attachments_returns_copy(attachment_handler, temp_image_file):
    """Test that pending_attachments property returns a copy."""
    attachment_handler.add_pending_attachment(temp_image_file, session_active=True)

    # Get list and modify it
    attachments = attachment_handler.pending_attachments
    attachments.append("/fake/path.png")

    # Original should be unchanged
    assert len(attachment_handler.pending_attachments) == 1
    assert "/fake/path.png" not in attachment_handler.pending_attachments


def test_signal_emits_copy(attachment_handler, temp_image_file, qtbot):
    """Test that signal emits a copy of the list."""
    received_list = []

    def on_changed(attachments):
        received_list.append(attachments)

    attachment_handler.pending_attachments_changed.connect(on_changed)

    attachment_handler.add_pending_attachment(temp_image_file, session_active=True)

    assert len(received_list) == 1
    # Modify received list
    received_list[0].append("/fake/path.png")
    # Original should be unchanged
    assert len(attachment_handler.pending_attachments) == 1
