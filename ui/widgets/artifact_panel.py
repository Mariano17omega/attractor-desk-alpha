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
    QMessageBox,
    QLineEdit,
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
from ui.widgets.pdf_viewer_widget import PdfViewerWidget


class CodeEditor(QPlainTextEdit):
    """Code editor with monospace font."""

    def __init__(self, parent=None):
        super().__init__(parent)

        font = QFont("JetBrains Mono", 12)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)

        self.setLineWrapMode(QPlainTextEdit.NoWrap)


class MarkdownViewer(QTextEdit):
    """Markdown viewer with double-click to edit support."""

    doubleClicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)

    def mouseDoubleClickEvent(self, event):
        """Emit doubleClicked signal on double-click."""
        self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)


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
        self._pdf_count = 0
        self._is_editing = False
        self._original_content = ""  # For cancel/revert
        self._is_renaming = False  # For title rename mode

        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self):
        """Setup the artifact panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.setObjectName("artifactPanel")
        self.setMinimumWidth(200)
        self.setMaximumWidth(1000)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        # Header area
        header_layout = QHBoxLayout()

        # Title display (clickable for rename)
        self.title_widget = QWidget()
        title_layout = QHBoxLayout(self.title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(8)

        self.title_label = QLabel("Artifact")
        self.title_label.setStyleSheet("font-size: 20px; font-weight: 600;")
        self.title_label.setCursor(Qt.PointingHandCursor)
        self.title_label.setToolTip("Double-click to rename")
        title_layout.addWidget(self.title_label)

        # Title edit (hidden by default)
        self.title_edit = QLineEdit()
        self.title_edit.setStyleSheet("font-size: 18px; font-weight: 600; padding: 2px 6px;")
        self.title_edit.setMaximumWidth(300)
        self.title_edit.hide()
        title_layout.addWidget(self.title_edit)

        # Title save button (hidden by default)
        self.title_save_button = QPushButton("✓")
        self.title_save_button.setFixedSize(28, 28)
        self.title_save_button.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; "
            "border-radius: 4px; }"
            "QPushButton:hover { background-color: #45a049; }"
        )
        self.title_save_button.setToolTip("Save name")
        self.title_save_button.hide()
        title_layout.addWidget(self.title_save_button)

        header_layout.addWidget(self.title_widget)
        header_layout.addStretch()


        # Delete artifact button (matches delete session button style)
        self.delete_button = QPushButton("-")
        self.delete_button.setObjectName("iconButton")
        self.delete_button.setToolTip("Delete artifact")
        self.delete_button.setFixedSize(32, 32)
        self.delete_button.setStyleSheet("font-size: 18px; font-weight: 700; padding: 0px;")
        header_layout.addWidget(self.delete_button)

        # Version navigation (shown in view mode)
        self.nav_widget = QWidget()
        nav_layout = QHBoxLayout(self.nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(4)

        self.prev_button = QPushButton("◀")
        self.prev_button.setMaximumWidth(40)
        self.prev_button.setEnabled(False)
        nav_layout.addWidget(self.prev_button)

        self.version_label = QLabel("v0/0")
        self.version_label.setStyleSheet("padding: 0 12px; font-size: 13px;")
        nav_layout.addWidget(self.version_label)

        self.next_button = QPushButton("▶")
        self.next_button.setMaximumWidth(40)
        self.next_button.setEnabled(False)
        nav_layout.addWidget(self.next_button)

        header_layout.addWidget(self.nav_widget)

        # Edit mode buttons (hidden by default)
        self.edit_buttons_widget = QWidget()
        edit_buttons_layout = QHBoxLayout(self.edit_buttons_widget)
        edit_buttons_layout.setContentsMargins(0, 0, 0, 0)
        edit_buttons_layout.setSpacing(8)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("cancelButton")
        edit_buttons_layout.addWidget(self.cancel_button)

        self.save_button = QPushButton("Save")
        self.save_button.setObjectName("saveButton")
        self.save_button.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: 600; "
            "padding: 6px 16px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #45a049; }"
        )
        edit_buttons_layout.addWidget(self.save_button)

        header_layout.addWidget(self.edit_buttons_widget)
        self.edit_buttons_widget.hide()

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

        # Text viewer (index 0)
        self.markdown_viewer = MarkdownViewer()
        self.content_stack.addWidget(self.markdown_viewer)

        # Code editor (index 1)
        self.code_editor = CodeEditor()
        self.content_stack.addWidget(self.code_editor)

        # Raw text editor for edit mode (index 2)
        self.raw_text_editor = QPlainTextEdit()
        self.raw_text_editor.setObjectName("rawTextEditor")
        font = QFont("JetBrains Mono", 12)
        font.setStyleHint(QFont.Monospace)
        self.raw_text_editor.setFont(font)
        self.content_stack.addWidget(self.raw_text_editor)

        # PDF viewer (index 3)
        self.pdf_viewer = PdfViewerWidget()
        self.content_stack.addWidget(self.pdf_viewer)

        content_layout.addWidget(self.content_stack)
        layout.addWidget(self.content_frame, stretch=1)

        # Placeholder with create button
        self.placeholder_widget = QWidget()
        placeholder_layout = QVBoxLayout(self.placeholder_widget)
        placeholder_layout.setAlignment(Qt.AlignCenter)

        self.placeholder = QLabel(
            "💡 Ask me to create something!\n\n"
            "Try: \"Write a poem about Python\"\n"
            "or \"Create a Python function to sort a list\""
        )
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.placeholder.setWordWrap(True)
        self.placeholder.setStyleSheet("font-size: 15px; padding: 20px 40px;")
        placeholder_layout.addWidget(self.placeholder)

        # Create artifact buttons
        create_buttons_layout = QHBoxLayout()
        create_buttons_layout.setAlignment(Qt.AlignCenter)
        create_buttons_layout.setSpacing(12)

        self.create_text_button = QPushButton("📝 New Text")
        self.create_text_button.setStyleSheet(
            "QPushButton { padding: 10px 20px; font-size: 14px; border-radius: 6px; }"
        )
        create_buttons_layout.addWidget(self.create_text_button)

        self.create_code_button = QPushButton("💻 New Code")
        self.create_code_button.setStyleSheet(
            "QPushButton { padding: 10px 20px; font-size: 14px; border-radius: 6px; }"
        )
        create_buttons_layout.addWidget(self.create_code_button)

        placeholder_layout.addLayout(create_buttons_layout)
        layout.addWidget(self.placeholder_widget)

        self._show_placeholder()

    def _setup_connections(self):
        """Setup signal/slot connections."""
        self.prev_button.clicked.connect(self._on_prev_version)
        self.next_button.clicked.connect(self._on_next_version)
        self.tab_bar.currentChanged.connect(self._on_tab_changed)

        # Edit mode connections
        self.markdown_viewer.doubleClicked.connect(self._start_edit_mode)
        self.save_button.clicked.connect(self._save_edit_mode)
        self.cancel_button.clicked.connect(self._cancel_edit_mode)

        # Create artifact buttons
        self.create_text_button.clicked.connect(lambda: self._create_new_artifact(is_code=False))
        self.create_code_button.clicked.connect(lambda: self._create_new_artifact(is_code=True))

        # Title rename connections
        self.title_label.installEventFilter(self)
        self.title_save_button.clicked.connect(self._save_title)
        self.title_edit.returnPressed.connect(self._save_title)

        # Delete artifact connection
        self.delete_button.clicked.connect(self._delete_artifact)

        # Connect to view model
        self.view_model.artifact_changed.connect(self._on_artifact_changed)
        self.pdf_viewer.page_changed.connect(self._on_pdf_page_changed)

    def _show_placeholder(self):
        """Show the empty state placeholder."""
        # Reset edit mode if active
        if self._is_editing:
            self._force_exit_edit_mode()

        self.content_frame.hide()
        self.tab_bar.hide()
        self.placeholder_widget.show()
        self.type_label.setText("No artifact generated yet")
        self.version_label.setText("v0/0")
        self.prev_button.setEnabled(False)
        self.next_button.setEnabled(False)
        self.nav_widget.show()
        self.edit_buttons_widget.hide()

    def _show_content(self):
        """Show the content area."""
        self.placeholder_widget.hide()
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
                elif current_content.type == "pdf":
                    self._pdf_count += 1
                    tab_label = f"PDF_{self._pdf_count}"
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
        elif current_content.type == "pdf":
            self.type_label.setText("📄 PDF Document")
            self.pdf_viewer.load_pdf(current_content.pdf_path)
            self.pdf_viewer.set_page(max(0, current_content.current_page - 1))
            self.pdf_viewer.set_status("Ready")
            self.content_stack.setCurrentIndex(3)  # Show PDF view
        else:
            self.type_label.setText("📝 Text Document")
            self.markdown_viewer.setMarkdown(current_content.full_markdown)
            self.content_stack.setCurrentIndex(0)  # Show text view

        if self._collection and self._collection.active_artifact_id:
            self.view_model.on_artifact_selected(self._collection.active_artifact_id)

    def _on_pdf_page_changed(self, page_index: int) -> None:
        if not self._collection:
            return
        active_entry = self._collection.get_active_entry()
        if not active_entry or not active_entry.artifact.contents:
            return
        current_content = active_entry.artifact.contents[-1]
        if current_content.type != "pdf":
            return
        current_content.current_page = page_index + 1
        session_id = self.view_model.current_session_id
        if session_id:
            self.view_model._artifact_repository.save_collection(session_id, self._collection)
        self.view_model._artifact = active_entry.artifact

    def _start_edit_mode(self):
        """Enter edit mode for the current text artifact."""
        if self._is_editing:
            return

        # Only support text artifacts for now
        artifact = self.view_model.current_artifact
        if not artifact or not artifact.contents:
            return

        current_content = None
        for content in artifact.contents:
            if content.index == artifact.current_index:
                current_content = content
                break

        if not current_content:
            current_content = artifact.contents[-1]

        # Only edit text artifacts (not code - code editor already editable)
        if current_content.type != "text":
            return

        self._is_editing = True
        self._original_content = current_content.full_markdown

        # Switch to raw text editor with markdown content
        self.raw_text_editor.setPlainText(current_content.full_markdown)
        self.content_stack.setCurrentIndex(2)  # Show raw text editor

        # Update UI: hide nav, show edit buttons
        self.nav_widget.hide()
        self.edit_buttons_widget.show()
        self.tab_bar.setEnabled(False)
        self.type_label.setText("✏️ Editing...")

    def _save_edit_mode(self):
        """Save changes and exit edit mode."""
        if not self._is_editing:
            return

        new_content = self.raw_text_editor.toPlainText()

        # Update the artifact in the COLLECTION (not view_model which is a separate reference)
        session_id = self.view_model.current_session_id
        if session_id and self._collection:
            # Get the active entry from the collection
            active_entry = self._collection.get_active_entry()
            if active_entry and active_entry.artifact.contents:
                artifact = active_entry.artifact
                for content in artifact.contents:
                    if content.index == artifact.current_index and content.type == "text":
                        content.full_markdown = new_content
                        break

                # Also sync to view_model so UI stays consistent
                self.view_model._artifact = artifact

            # Persist to repository
            self.view_model._artifact_repository.save_collection(
                session_id, self._collection
            )

        self._exit_edit_mode()

        # Refresh display with saved content
        self.markdown_viewer.setMarkdown(new_content)

    def _cancel_edit_mode(self):
        """Discard changes and exit edit mode."""
        if not self._is_editing:
            return

        self._exit_edit_mode()

        # Restore original rendered markdown
        self.markdown_viewer.setMarkdown(self._original_content)

    def _exit_edit_mode(self):
        """Common logic to exit edit mode (used by save and cancel)."""
        self._is_editing = False
        self._original_content = ""

        # Switch back to markdown viewer
        self.content_stack.setCurrentIndex(0)

        # Update UI: show nav, hide edit buttons
        self.nav_widget.show()
        self.edit_buttons_widget.hide()
        self.tab_bar.setEnabled(True)
        self.type_label.setText("📝 Text Document")

    def _force_exit_edit_mode(self):
        """Force exit edit mode without saving (used when switching sessions)."""
        self._is_editing = False
        self._original_content = ""
        self.content_stack.setCurrentIndex(0)
        self.nav_widget.show()
        self.edit_buttons_widget.hide()
        self.tab_bar.setEnabled(True)

    def check_pending_edits(self) -> bool:
        """Check for unsaved edits and prompt user.
        
        Returns:
            True if safe to proceed (no edits or user chose to discard)
            False if user chose to cancel
        """
        if not self._is_editing:
            return True

        reply = QMessageBox.warning(
            self,
            "Unsaved Changes",
            "You have unsaved changes to the artifact.\n\n"
            "Do you want to discard these changes?",
            QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Cancel
        )

        if reply == QMessageBox.Discard:
            self._force_exit_edit_mode()
            return True
        return False

    def eventFilter(self, watched, event):
        """Handle double-click on title label to enter rename mode."""
        from PySide6.QtCore import QEvent
        if watched == self.title_label and event.type() == QEvent.MouseButtonDblClick:
            self._start_rename_mode()
            return True
        return super().eventFilter(watched, event)

    def _start_rename_mode(self):
        """Enter title rename mode."""
        if self._is_renaming:
            return

        self._is_renaming = True
        current_title = self.title_label.text()
        self.title_edit.setText(current_title)
        self.title_label.hide()
        self.title_edit.show()
        self.title_save_button.show()
        self.title_edit.setFocus()
        self.title_edit.selectAll()

    def _save_title(self):
        """Save the new title and exit rename mode."""
        if not self._is_renaming:
            return

        new_title = self.title_edit.text().strip()
        if not new_title:
            new_title = "Untitled"  # Fallback

        # Update artifact title
        session_id = self.view_model.current_session_id
        if session_id and self._collection:
            active_entry = self._collection.get_active_entry()
            if active_entry and active_entry.artifact.contents:
                artifact = active_entry.artifact
                for content in artifact.contents:
                    if content.index == artifact.current_index:
                        content.title = new_title
                        break
                # Persist changes
                self.view_model._artifact_repository.save_collection(
                    session_id, self._collection
                )

        # Update UI
        self.title_label.setText(new_title)
        self._exit_rename_mode()

    def _exit_rename_mode(self):
        """Exit rename mode."""
        self._is_renaming = False
        self.title_edit.hide()
        self.title_save_button.hide()
        self.title_label.show()

    def _delete_artifact(self):
        """Delete the current artifact after confirmation."""
        if not self._collection or not self._collection.active_artifact_id:
            return

        active_entry = self._collection.get_active_entry()
        if not active_entry:
            return

        # Confirm deletion
        reply = QMessageBox.warning(
            self,
            "Delete Artifact",
            f"Delete artifact '{active_entry.artifact.contents[-1].title}'?\n\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        session_id = self.view_model.current_session_id
        if not session_id:
            return

        # Remove artifact from collection
        artifact_id = self._collection.active_artifact_id
        self._collection.artifacts = [
            e for e in self._collection.artifacts if e.id != artifact_id
        ]

        # Select next artifact or clear
        if self._collection.artifacts:
            self._collection.active_artifact_id = self._collection.artifacts[0].id
            self.view_model._artifact = self._collection.get_active_artifact()
        else:
            self._collection.active_artifact_id = None
            self.view_model._artifact = None

        # Persist and refresh
        self.view_model._artifact_repository.save_collection(session_id, self._collection)
        self.view_model.artifact_changed.emit()
