"""
Artifact panel widget for Open Canvas with multi-artifact support.

Implements dynamic Art_N/Code_N tabs for multiple artifacts per session,
plus New_Art and New_Code tabs for creating new artifacts.
"""

from typing import Optional
from uuid import uuid4

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPlainTextEdit,
    QPushButton,
    QFrame,
    QTabBar,
    QStackedWidget,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from core.types import (
    ArtifactCollectionV1,
    ArtifactEntry,
    ArtifactExportMeta,
    ArtifactMarkdownV3,
    ArtifactCodeV3,
    ArtifactV3,
    ProgrammingLanguageOptions,
)
from ui.viewmodels.chat_viewmodel import ChatViewModel


class CodeEditor(QPlainTextEdit):
    """Code editor with monospace font."""

    def __init__(self, parent=None):
        super().__init__(parent)

        font = QFont("JetBrains Mono", 12)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)

        self.setLineWrapMode(QPlainTextEdit.NoWrap)


class MarkdownViewer(QTextEdit):
    """Markdown viewer (read-only)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)


class ArtifactPanel(QWidget):
    """Artifact display panel with multi-artifact tab support.

    Features:
    - Dynamic Art_N / Code_N tabs based on artifacts in the collection
    - New_Art / New_Code tabs for creating blank artifacts
    - Single content area that toggles based on active artifact type
    - Version navigation for the active artifact
    """

    artifact_selected = Signal(str)  # Emits artifact ID when selected

    def __init__(self, view_model: ChatViewModel, parent=None):
        super().__init__(parent)

        self.view_model = view_model
        self._collection: Optional[ArtifactCollectionV1] = None
        self._text_count = 0
        self._code_count = 0

        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self):
        """Setup the artifact panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.setObjectName("artifactPanel")

        # Header area
        header_layout = QHBoxLayout()

        self.title_label = QLabel("Artifact")
        self.title_label.setStyleSheet("font-size: 20px; font-weight: 600;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        # Version navigation
        self.prev_button = QPushButton("◀")
        self.prev_button.setMaximumWidth(40)
        self.prev_button.setEnabled(False)
        header_layout.addWidget(self.prev_button)

        self.version_label = QLabel("v0/0")
        self.version_label.setStyleSheet("padding: 0 12px; font-size: 13px;")
        header_layout.addWidget(self.version_label)

        self.next_button = QPushButton("▶")
        self.next_button.setMaximumWidth(40)
        self.next_button.setEnabled(False)
        header_layout.addWidget(self.next_button)

        layout.addLayout(header_layout)

        # Type indicator
        self.type_label = QLabel("No artifact generated yet")
        self.type_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.type_label)

        # Dynamic artifact tabs
        self.tab_bar = QTabBar()
        self.tab_bar.setExpanding(False)
        self.tab_bar.setDocumentMode(True)
        layout.addWidget(self.tab_bar)

        # Content area (stacked widget for markdown/code views)
        self.content_frame = QFrame()
        self.content_frame.setObjectName("artifactContent")

        content_layout = QVBoxLayout(self.content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self.content_stack = QStackedWidget()

        # Text viewer
        self.markdown_viewer = MarkdownViewer()
        self.content_stack.addWidget(self.markdown_viewer)

        # Code editor
        self.code_editor = CodeEditor()
        self.content_stack.addWidget(self.code_editor)

        content_layout.addWidget(self.content_stack)
        layout.addWidget(self.content_frame, stretch=1)

        # Placeholder
        self.placeholder = QLabel(
            "💡 Ask me to create something!\n\n"
            "Try: \"Write a poem about Python\"\n"
            "or \"Create a Python function to sort a list\""
        )
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.placeholder.setWordWrap(True)
        self.placeholder.setStyleSheet("font-size: 15px; padding: 60px 40px;")
        layout.addWidget(self.placeholder)

        self._show_placeholder()

    def _setup_connections(self):
        """Setup signal/slot connections."""
        self.prev_button.clicked.connect(self._on_prev_version)
        self.next_button.clicked.connect(self._on_next_version)
        self.tab_bar.currentChanged.connect(self._on_tab_changed)

        # Connect to view model
        self.view_model.artifact_changed.connect(self._on_artifact_changed)

    def _show_placeholder(self):
        """Show the empty state placeholder."""
        self.content_frame.hide()
        self.tab_bar.hide()
        self.placeholder.show()
        self.type_label.setText("No artifact generated yet")
        self.version_label.setText("v0/0")
        self.prev_button.setEnabled(False)
        self.next_button.setEnabled(False)

    def _show_content(self):
        """Show the content area."""
        self.placeholder.hide()
        self.tab_bar.show()
        self.content_frame.show()

    def _rebuild_tabs(self, collection: ArtifactCollectionV1):
        """Rebuild the tab bar based on the artifact collection."""
        # Clear existing tabs
        while self.tab_bar.count() > 0:
            self.tab_bar.removeTab(0)

        self._text_count = 0
        self._code_count = 0

        # Track tab index to artifact ID mapping
        self._tab_artifact_ids: list[Optional[str]] = []

        # Add tabs for each artifact
        for entry in collection.artifacts:
            artifact = entry.artifact
            if artifact.contents:
                current_content = artifact.contents[-1]
                if current_content.type == "code":
                    self._code_count += 1
                    tab_label = f"Code_{self._code_count}"
                else:
                    self._text_count += 1
                    tab_label = f"Art_{self._text_count}"

                self.tab_bar.addTab(tab_label)
                self._tab_artifact_ids.append(entry.id)

        # Add "New" tabs
        self.tab_bar.addTab("+ Art")
        self._tab_artifact_ids.append(None)  # Special marker for new text

        self.tab_bar.addTab("+ Code")
        self._tab_artifact_ids.append(None)  # Special marker for new code

        # Select active artifact tab
        if collection.active_artifact_id:
            for i, aid in enumerate(self._tab_artifact_ids):
                if aid == collection.active_artifact_id:
                    self.tab_bar.setCurrentIndex(i)
                    break

    def _on_tab_changed(self, index: int):
        """Handle tab selection change."""
        if index < 0 or index >= len(self._tab_artifact_ids):
            return

        artifact_id = self._tab_artifact_ids[index]

        if artifact_id is None:
            # "New" tab selected - determine if it's Art or Code
            tab_text = self.tab_bar.tabText(index)
            if "Art" in tab_text:
                self._create_new_artifact(is_code=False)
            else:
                self._create_new_artifact(is_code=True)
        else:
            # Existing artifact selected
            self._select_artifact(artifact_id)

    def _create_new_artifact(self, is_code: bool):
        """Create a new blank artifact."""
        session_id = self.view_model.current_session_id
        if not session_id:
            return

        if is_code:
            content = ArtifactCodeV3(
                index=1,
                type="code",
                title="New Code",
                language=ProgrammingLanguageOptions.PYTHON,
                code="# New code artifact\n",
            )
        else:
            content = ArtifactMarkdownV3(
                index=1,
                type="text",
                title="New Text",
                fullMarkdown="# New text artifact\n",
            )

        new_artifact = ArtifactV3(
            currentIndex=1,
            contents=[content],
        )
        entry = ArtifactEntry(
            id=str(uuid4()),
            artifact=new_artifact,
            export_meta=ArtifactExportMeta(),
        )

        # Get or create collection
        collection = self.view_model._artifact_repository.get_collection(session_id)
        if collection is None:
            collection = ArtifactCollectionV1(
                version=1,
                artifacts=[entry],
                active_artifact_id=entry.id,
            )
        else:
            collection.artifacts.append(entry)
            collection.active_artifact_id = entry.id

        self.view_model._artifact_repository.save_collection(session_id, collection)
        self.view_model._artifact = new_artifact
        self.view_model.artifact_changed.emit()

    def _select_artifact(self, artifact_id: str):
        """Select an artifact by ID."""
        session_id = self.view_model.current_session_id
        if not session_id:
            return

        collection = self.view_model._artifact_repository.get_collection(session_id)
        if collection is None:
            return

        if collection.set_active_artifact(artifact_id):
            self.view_model._artifact_repository.save_collection(session_id, collection)
            self.view_model._artifact = collection.get_active_artifact()
            self.artifact_selected.emit(artifact_id)
            self._update_display(collection)

    def _on_prev_version(self):
        """Navigate to previous artifact version."""
        self.view_model.prev_artifact_version()

    def _on_next_version(self):
        """Navigate to next artifact version."""
        self.view_model.next_artifact_version()

    def _on_artifact_changed(self):
        """Handle artifact changes from view model."""
        session_id = self.view_model.current_session_id
        if not session_id:
            self._show_placeholder()
            return

        collection = self.view_model._artifact_repository.get_collection(session_id)
        if collection is None or not collection.artifacts:
            self._show_placeholder()
            return

        self._collection = collection
        self._rebuild_tabs(collection)
        self._update_display(collection)

    def _update_display(self, collection: ArtifactCollectionV1):
        """Update the display for the active artifact."""
        artifact = collection.get_active_artifact()

        if not artifact or not artifact.contents:
            self._show_placeholder()
            return

        self._show_content()

        # Get current content
        current_content = None
        for content in artifact.contents:
            if content.index == artifact.current_index:
                current_content = content
                break

        if not current_content:
            current_content = artifact.contents[-1]

        # Update title
        self.title_label.setText(current_content.title)

        # Update version info
        total_versions = len(artifact.contents)
        self.version_label.setText(f"v{artifact.current_index}/{total_versions}")

        # Update navigation buttons
        self.prev_button.setEnabled(artifact.current_index > 1)
        self.next_button.setEnabled(artifact.current_index < total_versions)

        # Update content
        if current_content.type == "code":
            lang_value = (
                current_content.language.value
                if hasattr(current_content.language, "value")
                else str(current_content.language)
            )
            self.type_label.setText(f"💻 Code • {lang_value.title()}")
            self.code_editor.setPlainText(current_content.code)
            self.content_stack.setCurrentIndex(1)  # Show code view
        else:
            self.type_label.setText("📝 Text Document")
            self.markdown_viewer.setMarkdown(current_content.full_markdown)
            self.content_stack.setCurrentIndex(0)  # Show text view
