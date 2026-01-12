"""
Artifact panel widget for Open Canvas.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPlainTextEdit,
    QPushButton,
    QFrame,
    QTabWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.viewmodels.chat_viewmodel import ChatViewModel


class CodeEditor(QPlainTextEdit):
    """Code editor with monospace font and light theme."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Set monospace font
        font = QFont("JetBrains Mono", 12)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)
        
        # Light theme for code
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #f8f9fa;
                color: #1a1a1a;
                border: none;
                padding: 16px;
                line-height: 1.5;
            }
        """)
        
        self.setLineWrapMode(QPlainTextEdit.NoWrap)


class MarkdownViewer(QTextEdit):
    """Markdown viewer (read-only) with light theme."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setReadOnly(True)
        self.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                color: #1a1a1a;
                border: none;
                padding: 20px;
                font-size: 15px;
                line-height: 1.6;
            }
        """)


class ArtifactPanel(QWidget):
    """Artifact display panel with version navigation."""
    
    def __init__(self, view_model: ChatViewModel, parent=None):
        super().__init__(parent)
        
        self.view_model = view_model
        
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self):
        """Setup the artifact panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
            }
        """)
        
        # Header area
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel("Artifact")
        self.title_label.setStyleSheet("""
            font-size: 20px;
            font-weight: 600;
            color: #1a1a1a;
        """)
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        # Version navigation
        self.prev_button = QPushButton("◀")
        self.prev_button.setMaximumWidth(40)
        self.prev_button.setEnabled(False)
        self.prev_button.setStyleSheet("""
            QPushButton {
                background-color: #e8e8e8;
                color: #1a1a1a;
                border: none;
                padding: 8px;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #d8d8d8;
            }
            QPushButton:disabled {
                color: #aaaaaa;
            }
        """)
        header_layout.addWidget(self.prev_button)
        
        self.version_label = QLabel("v0/0")
        self.version_label.setStyleSheet("""
            padding: 0 12px;
            color: #666666;
            font-size: 13px;
        """)
        header_layout.addWidget(self.version_label)
        
        self.next_button = QPushButton("▶")
        self.next_button.setMaximumWidth(40)
        self.next_button.setEnabled(False)
        self.next_button.setStyleSheet("""
            QPushButton {
                background-color: #e8e8e8;
                color: #1a1a1a;
                border: none;
                padding: 8px;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #d8d8d8;
            }
            QPushButton:disabled {
                color: #aaaaaa;
            }
        """)
        header_layout.addWidget(self.next_button)
        
        layout.addLayout(header_layout)
        
        # Type indicator
        self.type_label = QLabel("No artifact generated yet")
        self.type_label.setStyleSheet("""
            color: #888888;
            font-size: 13px;
        """)
        layout.addWidget(self.type_label)
        
        # Content area
        self.content_frame = QFrame()
        self.content_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
            }
        """)
        
        content_layout = QVBoxLayout(self.content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Tab widget for code/text views
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.South)
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #ffffff;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                color: #666666;
                padding: 10px 20px;
                margin-right: 2px;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #1a1a1a;
                font-weight: 600;
            }
        """)
        
        # Text viewer
        self.markdown_viewer = MarkdownViewer()
        self.tabs.addTab(self.markdown_viewer, "📝 Text")
        
        # Code editor
        self.code_editor = CodeEditor()
        self.tabs.addTab(self.code_editor, "💻 Code")
        
        content_layout.addWidget(self.tabs)
        layout.addWidget(self.content_frame, stretch=1)
        
        # Placeholder
        self.placeholder = QLabel("💡 Ask me to create something!\n\nTry: \"Write a poem about Python\"\nor \"Create a Python function to sort a list\"")
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.placeholder.setWordWrap(True)
        self.placeholder.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 15px;
                padding: 60px 40px;
                line-height: 1.8;
            }
        """)
        layout.addWidget(self.placeholder)
        
        self._show_placeholder()
    
    def _setup_connections(self):
        """Setup signal/slot connections."""
        self.prev_button.clicked.connect(self._on_prev_version)
        self.next_button.clicked.connect(self._on_next_version)
        
        # Connect to view model
        self.view_model.artifact_changed.connect(self._on_artifact_changed)
    
    def _show_placeholder(self):
        """Show the empty state placeholder."""
        self.content_frame.hide()
        self.placeholder.show()
        self.type_label.setText("No artifact generated yet")
        self.version_label.setText("v0/0")
        self.prev_button.setEnabled(False)
        self.next_button.setEnabled(False)
    
    def _show_content(self):
        """Show the content area."""
        self.placeholder.hide()
        self.content_frame.show()
    
    def _on_prev_version(self):
        """Navigate to previous artifact version."""
        self.view_model.prev_artifact_version()
    
    def _on_next_version(self):
        """Navigate to next artifact version."""
        self.view_model.next_artifact_version()
    
    def _on_artifact_changed(self):
        """Handle artifact changes from view model."""
        artifact = self.view_model.current_artifact
        
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
            lang_value = current_content.language.value if hasattr(current_content.language, 'value') else str(current_content.language)
            self.type_label.setText(f"💻 Code • {lang_value.title()}")
            self.code_editor.setPlainText(current_content.code)
            self.tabs.setCurrentIndex(1)  # Show code tab
        else:
            self.type_label.setText("📝 Text Document")
            self.markdown_viewer.setMarkdown(current_content.full_markdown)
            self.tabs.setCurrentIndex(0)  # Show text tab
