"""Chat panel widget for message display and input."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Signal, Qt, QEvent
from PySide6.QtGui import QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.viewmodels.chat_viewmodel import ChatViewModel


AVATAR_SIZE = 32
PROFILE_DIR = Path(__file__).resolve().parents[1] / "assets" / "profile"


def _resolve_avatar_path(agent_name: str, is_user: bool) -> Optional[Path]:
    if is_user:
        candidate = PROFILE_DIR / "use.png"
        return candidate if candidate.exists() else None
    if not agent_name:
        return None
    normalized = agent_name.strip().lower()
    candidates = [normalized, "kurisu"]
    for name in candidates:
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            path = PROFILE_DIR / f"{name}{ext}"
            if path.exists():
                return path
    return None


def _create_avatar_label(agent_name: str, is_user: bool) -> QLabel:
    label = QLabel()
    label.setFixedSize(AVATAR_SIZE, AVATAR_SIZE)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setObjectName("userAvatar" if is_user else "assistantAvatar")
    avatar_path = _resolve_avatar_path(agent_name, is_user)
    if avatar_path:
        pixmap = QPixmap(str(avatar_path)).scaled(
            AVATAR_SIZE,
            AVATAR_SIZE,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        label.setPixmap(pixmap)
    else:
        label.setText("U" if is_user else "A")
    return label


class MessageBubble(QFrame):
    """Widget for displaying a single message."""

    def __init__(
        self,
        content: str,
        is_user: bool = False,
        agent_name: str = "Assistant",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("messageRow")

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 6, 10, 6)
        main_layout.setSpacing(12)

        avatar_label = _create_avatar_label(agent_name, is_user)

        bubble = QFrame()
        bubble.setObjectName("userMessage" if is_user else "assistantMessage")
        bubble.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)
        bubble.setMaximumWidth(600)

        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(12, 8, 12, 8)
        bubble_layout.setSpacing(4)

        if not is_user:
            role_label = QLabel(agent_name)
            role_label.setObjectName("roleLabel")
            role_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #9CA3AF;")
            bubble_layout.addWidget(role_label)

        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        content_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        bubble_layout.addWidget(content_label)

        if is_user:
            main_layout.addStretch()
            main_layout.addWidget(bubble, 0, Qt.AlignmentFlag.AlignTop)
            main_layout.addWidget(avatar_label, 0, Qt.AlignmentFlag.AlignTop)
        else:
            main_layout.addWidget(avatar_label, 0, Qt.AlignmentFlag.AlignTop)
            main_layout.addWidget(bubble, 0, Qt.AlignmentFlag.AlignTop)
            main_layout.addStretch()


class MessageInput(QTextEdit):
    """Text input with configurable shortcut to send and auto-resize behavior."""

    send_requested = Signal()
    MAX_HEIGHT = 150

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._send_sequence = QKeySequence("Ctrl+Return")
        self._update_placeholder()
        self.document().setDocumentMargin(0)
        self.setContentsMargins(0, 0, 0, 0)
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._min_height = self._calculate_min_height()
        self.setFixedHeight(self._min_height)
        self.textChanged.connect(self._adjust_height)

    def _calculate_min_height(self) -> int:
        line_height = self.fontMetrics().lineSpacing()
        doc_margin = self.document().documentMargin()
        margins = self.contentsMargins()
        frame_width = self.frameWidth()
        total_height = (
            line_height
            + 2 * doc_margin
            + margins.top()
            + margins.bottom()
            + 2 * frame_width
        )
        return int(total_height)

    def _refresh_min_height(self) -> None:
        new_min_height = self._calculate_min_height()
        if new_min_height != self._min_height:
            self._min_height = new_min_height
            self._adjust_height()

    def changeEvent(self, event) -> None:
        if event.type() in (QEvent.Type.StyleChange, QEvent.Type.FontChange):
            if hasattr(self, "_min_height"):
                self._refresh_min_height()
        super().changeEvent(event)

    def _adjust_height(self) -> None:
        doc = self.document()
        doc.setTextWidth(self.viewport().width())
        doc_height = doc.size().height()
        margins = self.contentsMargins()
        frame_width = self.frameWidth()
        total_height = int(doc_height + margins.top() + margins.bottom() + 2 * frame_width)
        new_height = max(self._min_height, min(total_height, self.MAX_HEIGHT))
        if total_height > self.MAX_HEIGHT:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        if self.height() != new_height:
            self.setFixedHeight(new_height)

    def set_send_sequence(self, sequence: str) -> None:
        self._send_sequence = QKeySequence(sequence) if sequence else QKeySequence()
        self._update_placeholder()

    def _update_placeholder(self) -> None:
        sequence_text = self._send_sequence.toString() or "Ctrl+Return"
        self.setPlaceholderText(f"Type your message... ({sequence_text} to send)")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if not self._send_sequence.isEmpty():
            pressed = QKeySequence(event.keyCombination())
            if (
                self._send_sequence.matches(pressed)
                == QKeySequence.SequenceMatch.ExactMatch
            ):
                self.send_requested.emit()
                return
        if (
            event.key() == Qt.Key.Key_Return
            and event.modifiers() == Qt.KeyboardModifier.ControlModifier
            and self._send_sequence.isEmpty()
        ):
            self.send_requested.emit()
        else:
            super().keyPressEvent(event)


class ChatPanel(QFrame):
    """Chat panel widget for displaying and sending messages."""

    sidebar_toggle_requested = Signal()
    memory_panel_requested = Signal()
    deep_search_toggle_requested = Signal()

    def __init__(
        self,
        viewmodel: ChatViewModel,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.viewmodel = viewmodel
        self.setObjectName("chatPanel")
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(64)
        header.setObjectName("chatHeader")

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 0, 24, 0)
        header_layout.setSpacing(12)

        title_container = QWidget()
        title_container.setStyleSheet("background-color: transparent;")
        title_layout_v = QVBoxLayout(title_container)
        title_layout_v.setContentsMargins(0, 0, 0, 0)
        title_layout_v.setSpacing(2)
        title_layout_v.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        title_row = QWidget()
        title_row.setStyleSheet("background-color: transparent;")
        title_row_layout = QHBoxLayout(title_row)
        title_row_layout.setContentsMargins(0, 0, 0, 0)
        title_row_layout.setSpacing(8)
        title_row_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        status_dot = QFrame()
        status_dot.setFixedSize(8, 8)
        status_dot.setStyleSheet("background-color: #00C2FF; border-radius: 4px;")
        title_row_layout.addWidget(status_dot)

        self._header_label = QLabel("AMADEUS CHANNEL")
        self._header_label.setObjectName("headerLabel")
        title_row_layout.addWidget(self._header_label)

        title_layout_v.addWidget(title_row)

        subtitle = QLabel("SECURE CONNECTION // AMADEUS PROTOCOL V1.02")
        subtitle.setStyleSheet(
            "color: #6B7280; font-size: 8px; font-weight: bold; letter-spacing: 1.5px; "
            "background-color: transparent; padding-left: 16px;"
        )
        subtitle.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title_layout_v.addWidget(subtitle)

        header_layout.addWidget(title_container)
        header_layout.addStretch()

        right_container = QWidget()
        right_container.setStyleSheet("background-color: transparent;")
        right_layout = QHBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        agent_label = QLabel("PROTOCOL:")
        agent_label.setStyleSheet(
            "color: #6B7280; font-size: 10px; font-weight: bold; letter-spacing: 1px;"
        )
        right_layout.addWidget(agent_label)

        self._agent_combo = QComboBox()
        self._agent_combo.setMinimumWidth(150)
        self._agent_combo.addItem("Default")
        self._agent_combo.setToolTip("Select agent for this chat")
        self._agent_combo.setAccessibleName("Agent selector")
        self._agent_combo.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        right_layout.addWidget(self._agent_combo)

        self._memory_btn = QPushButton("⛁ (0)")
        self._memory_btn.setObjectName("iconButton")
        self._memory_btn.setFixedSize(52, 32)
        self._memory_btn.setToolTip("Toggle artifacts panel")
        self._memory_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._memory_btn.clicked.connect(self.memory_panel_requested.emit)
        right_layout.addWidget(self._memory_btn)

        self._sidebar_toggle_btn = QPushButton("☰")
        self._sidebar_toggle_btn.setObjectName("iconButton")
        self._sidebar_toggle_btn.setFixedSize(32, 32)
        self._sidebar_toggle_btn.setToolTip("Toggle sidebar")
        self._sidebar_toggle_btn.setStyleSheet(
            "font-size: 16px; font-weight: bold; outline: none; border: none;"
        )
        self._sidebar_toggle_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._sidebar_toggle_btn.clicked.connect(self.sidebar_toggle_requested.emit)
        right_layout.addWidget(self._sidebar_toggle_btn)

        header_layout.addWidget(right_container)
        layout.addWidget(header)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self._messages_container = QWidget()
        self._messages_layout = QVBoxLayout(self._messages_container)
        self._messages_layout.setContentsMargins(0, 20, 0, 20)
        self._messages_layout.setSpacing(16)

        self._history_loader = QPushButton("Load older messages...")
        self._history_loader.setObjectName("historyLoader")
        self._history_loader.setVisible(False)
        self._messages_layout.addWidget(self._history_loader)

        self._messages_layout.addStretch()

        self._scroll_area.setWidget(self._messages_container)
        layout.addWidget(self._scroll_area, 1)

        bottom_container = QWidget()
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(24, 12, 24, 16)
        bottom_layout.setSpacing(8)

        input_row = QWidget()
        input_row.setObjectName("chatInputRow")
        input_row_layout = QHBoxLayout(input_row)
        input_row_layout.setContentsMargins(0, 0, 0, 0)
        input_row_layout.setSpacing(12)

        # Deep Search toggle button - toggles internet access for the agent
        self._deep_search_btn = QPushButton("🌐")
        self._deep_search_btn.setFixedSize(32, 32)
        self._deep_search_btn.setToolTip("Toggle Deep Search (internet access)")
        self._deep_search_btn.setCheckable(True)
        self._deep_search_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._update_deep_search_style(False)
        input_row_layout.addWidget(self._deep_search_btn)

        self._add_btn = QPushButton("+")
        self._add_btn.setObjectName("iconButton")
        self._add_btn.setToolTip("Import PDF as artifact")
        self._add_btn.setFixedSize(32, 32)
        self._add_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        input_row_layout.addWidget(self._add_btn)


        self._message_input = MessageInput()
        self._message_input.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        input_row_layout.addWidget(self._message_input, 1)

        self._send_btn = QPushButton("➤")
        self._send_btn.setFixedSize(32, 32)
        self._send_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #00C2FF;
                color: white;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3CBFF2;
            }
            """
        )
        self._send_btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        input_row_layout.addWidget(self._send_btn)

        self._cancel_btn = QPushButton("■")
        self._cancel_btn.setFixedSize(32, 32)
        self._cancel_btn.setVisible(False)
        self._cancel_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #EF4444;
                color: white;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F87171;
            }
            """
        )
        self._cancel_btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        input_row_layout.addWidget(self._cancel_btn)

        bottom_layout.addWidget(input_row)
        layout.addWidget(bottom_container)

    def _connect_signals(self) -> None:
        self._message_input.send_requested.connect(self._send_message)
        self._send_btn.clicked.connect(self._send_message)
        self._cancel_btn.clicked.connect(self.viewmodel.cancel_generation)
        self._add_btn.clicked.connect(self._on_add_clicked)
        self._deep_search_btn.clicked.connect(self._on_deep_search_toggled)
        self.viewmodel.pdf_import_status.connect(self._on_pdf_status)
        self.view_model_signals()


    def view_model_signals(self) -> None:
        self.viewmodel.message_added.connect(self._on_message_added)
        self.viewmodel.messages_loaded.connect(self._on_messages_loaded)
        self.viewmodel.is_loading_changed.connect(self._on_loading_changed)

    def _send_message(self) -> None:
        content = self._message_input.toPlainText().strip()
        if not content:
            return
        self._message_input.clear()
        self.viewmodel.send_message(content)

    def _on_message_added(self, content: str, is_user: bool) -> None:
        bubble = MessageBubble(content, is_user)
        self._messages_layout.insertWidget(
            self._messages_layout.count() - 1, bubble
        )
        self._scroll_to_bottom()

    def _on_messages_loaded(self, messages: list[dict]) -> None:
        self._clear_messages()
        for message in messages:
            bubble = MessageBubble(
                message.get("content", ""),
                message.get("is_user", False),
            )
            self._messages_layout.insertWidget(
                self._messages_layout.count() - 1, bubble
            )
        self._scroll_to_bottom()

    def _on_loading_changed(self, is_loading: bool) -> None:
        self._send_btn.setVisible(not is_loading)
        self._cancel_btn.setVisible(is_loading)
        self._message_input.setEnabled(not is_loading)

    def _scroll_to_bottom(self) -> None:
        self._scroll_area.verticalScrollBar().setValue(
            self._scroll_area.verticalScrollBar().maximum()
        )

    def _clear_messages(self) -> None:
        for index in range(self._messages_layout.count() - 2, 0, -1):
            item = self._messages_layout.takeAt(index)
            if item and item.widget():
                item.widget().deleteLater()

    def update_memory_count(self, count: int) -> None:
        self._memory_btn.setText(f"⛁ ({count})")

    def focus_input(self) -> None:
        self._message_input.setFocus()

    def _on_add_clicked(self) -> None:
        """Open PDF file dialog and import selected file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF to Import",
            "",
            "PDF Files (*.pdf)",
        )
        if file_path:
            self.viewmodel.import_pdf(file_path)

    def _on_pdf_status(self, status: str) -> None:
        """Display PDF import status in the chat."""
        if status:
            self.viewmodel.status_changed.emit(status)

    def set_deep_search_enabled(self, enabled: bool) -> None:
        """Update the Deep Search button state based on enabled setting."""
        self._deep_search_btn.setChecked(enabled)
        self._update_deep_search_style(enabled)

    def _update_deep_search_style(self, enabled: bool) -> None:
        """Update the Deep Search button style based on state."""
        if enabled:
            self._deep_search_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: rgba(0, 194, 255, 0.3);
                    border: 1px solid #00C2FF;
                    border-radius: 6px;
                    font-size: 16px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 194, 255, 0.4);
                }
                """
            )
            self._deep_search_btn.setToolTip("Deep Search enabled (click to disable)")
        else:
            self._deep_search_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: rgba(108, 112, 134, 0.2);
                    border: 1px solid transparent;
                    border-radius: 6px;
                    font-size: 16px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: rgba(108, 112, 134, 0.3);
                    border: 1px solid #6c7086;
                }
                """
            )
            self._deep_search_btn.setToolTip("Deep Search disabled (click to enable)")

    def _on_deep_search_toggled(self, checked: bool) -> None:
        """Handle Deep Search button toggle."""
        self._update_deep_search_style(checked)
        self.deep_search_toggle_requested.emit()
