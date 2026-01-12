"""
Chat panel widget for Open Canvas.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QScrollArea,
    QLabel,
    QFrame,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent

from ui.viewmodels.chat_viewmodel import ChatViewModel


class MessageBubble(QFrame):
    """A single message bubble in the chat."""
    
    def __init__(self, content: str, is_user: bool = False, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)
        
        # Role label
        role_label = QLabel("You" if is_user else "Assistant")
        role_label.setStyleSheet("""
            font-weight: 600;
            font-size: 12px;
            color: #666666;
        """)
        layout.addWidget(role_label)
        
        # Content label
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        content_label.setStyleSheet("""
            font-size: 14px;
            line-height: 1.5;
            color: #1a1a1a;
        """)
        layout.addWidget(content_label)
        
        # Styling based on role
        if is_user:
            self.setStyleSheet("""
                QFrame {
                    background-color: #e8f4fd;
                    border-radius: 12px;
                    margin-left: 60px;
                    margin-right: 8px;
                    margin-top: 4px;
                    margin-bottom: 4px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #f5f5f5;
                    border-radius: 12px;
                    margin-left: 8px;
                    margin-right: 60px;
                    margin-top: 4px;
                    margin-bottom: 4px;
                }
            """)


class ChatInput(QTextEdit):
    """Custom text input with Enter to send support."""
    
    submitted = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Type your message here... (Enter to send, Shift+Enter for new line)")
        self.setMaximumHeight(120)
        self.setMinimumHeight(50)
        self.setStyleSheet("""
            QTextEdit {
                border: 1px solid #d0d0d0;
                border-radius: 12px;
                padding: 12px;
                font-size: 14px;
                background-color: #ffffff;
                color: #1a1a1a;
            }
            QTextEdit:focus {
                border-color: #4a90d9;
            }
        """)
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events."""
        if event.key() == Qt.Key_Return and not event.modifiers():
            # Enter without modifiers sends the message
            text = self.toPlainText().strip()
            if text:
                self.submitted.emit(text)
                self.clear()
            return
        super().keyPressEvent(event)


class ChatPanel(QWidget):
    """Chat panel with message history and input."""
    
    def __init__(self, view_model: ChatViewModel, parent=None):
        super().__init__(parent)
        
        self.view_model = view_model
        
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self):
        """Setup the chat panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
            }
        """)
        
        # Header
        header_layout = QHBoxLayout()
        header = QLabel("Chat")
        header.setStyleSheet("""
            font-size: 20px;
            font-weight: 600;
            color: #1a1a1a;
        """)
        header_layout.addWidget(header)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Messages area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #e8e8e8;
                border-radius: 12px;
                background-color: #fafafa;
            }
        """)
        
        self.messages_container = QWidget()
        self.messages_container.setStyleSheet("background-color: #fafafa;")
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setAlignment(Qt.AlignTop)
        self.messages_layout.setSpacing(8)
        self.messages_layout.setContentsMargins(8, 8, 8, 8)
        
        # Welcome message
        self.welcome_label = QLabel("Start a conversation by typing a message below.")
        self.welcome_label.setAlignment(Qt.AlignCenter)
        self.welcome_label.setStyleSheet("""
            color: #888888;
            font-size: 14px;
            padding: 40px;
        """)
        self.messages_layout.addWidget(self.welcome_label)
        
        self.scroll_area.setWidget(self.messages_container)
        layout.addWidget(self.scroll_area, stretch=1)
        
        # Input area
        input_layout = QHBoxLayout()
        input_layout.setSpacing(12)
        
        self.input_field = ChatInput()
        input_layout.addWidget(self.input_field, stretch=1)
        
        self.send_button = QPushButton("Send")
        self.send_button.setMinimumWidth(80)
        self.send_button.setMinimumHeight(50)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #4a90d9;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3a7fc8;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        input_layout.addWidget(self.send_button)
        
        layout.addLayout(input_layout)
    
    def _setup_connections(self):
        """Setup signal/slot connections."""
        self.send_button.clicked.connect(self._on_send)
        self.input_field.submitted.connect(self._on_submit)
        
        # Connect to view model
        self.view_model.message_added.connect(self._on_message_added)
        self.view_model.is_loading_changed.connect(self._on_loading_changed)
    
    def _on_send(self):
        """Handle send button click."""
        text = self.input_field.toPlainText().strip()
        if text:
            self._on_submit(text)
            self.input_field.clear()
    
    def _on_submit(self, text: str):
        """Handle message submission."""
        self.view_model.send_message(text)
    
    def _on_message_added(self, content: str, is_user: bool):
        """Handle new message from view model."""
        # Hide welcome message
        self.welcome_label.hide()
        
        bubble = MessageBubble(content, is_user)
        self.messages_layout.addWidget(bubble)
        
        # Scroll to bottom
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )
    
    def _on_loading_changed(self, is_loading: bool):
        """Handle loading state changes."""
        self.send_button.setEnabled(not is_loading)
        self.input_field.setEnabled(not is_loading)
        
        if is_loading:
            self.send_button.setText("...")
        else:
            self.send_button.setText("Send")
    
    def clear_messages(self):
        """Clear all messages from the chat."""
        # Remove all message bubbles
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        
        # Show welcome message again
        self.welcome_label.show()
