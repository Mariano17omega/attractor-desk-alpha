"""Chat panel widget for message display and input with agent support."""

from typing import Optional

from PySide6.QtCore import Signal, Qt, QTimer, QPropertyAnimation, QEasingCurve, QEvent
from PySide6.QtGui import QKeyEvent, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QScrollBar,
    QScroller,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QGraphicsOpacityEffect,
)

from ..viewmodels import ChatViewModel
from .message_bubble import MessageBubble, StreamingMessageBubble


class MessageInput(QTextEdit):
    """Text input with configurable shortcut to send and auto-resize behavior."""
    
    send_requested = Signal()
    
    # Height constraints for auto-resize
    MAX_HEIGHT = 150
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the message input.
        
        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._send_sequence = QKeySequence("Ctrl+Return")
        self._update_placeholder()
        self.document().setDocumentMargin(0)
        self.setContentsMargins(0, 0, 0, 0)
        
        # Wrap at widget width so height tracks visual lines
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        
        # Start with scrollbar hidden - only show when at max height
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Set initial fixed height to minimum
        self._min_height = self._calculate_min_height()
        self.setFixedHeight(self._min_height)
        
        # Connect to text changes for auto-resize
        self.textChanged.connect(self._adjust_height)
    
    def _calculate_min_height(self) -> int:
        """Calculate the height needed for a single line of text."""
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
        """Handle style/font updates that can affect sizing."""
        if event.type() in (QEvent.Type.StyleChange, QEvent.Type.FontChange):
            if hasattr(self, "_min_height"):
                self._refresh_min_height()
        super().changeEvent(event)

    def _adjust_height(self) -> None:
        """Adjust the height of the input based on content."""
        # Force document layout to update
        doc = self.document()
        doc.setTextWidth(self.viewport().width())
        
        # Get the ideal height from the document
        doc_height = doc.size().height()
        
        # Add margins/padding
        margins = self.contentsMargins()
        frame_width = self.frameWidth()
        total_height = int(doc_height + margins.top() + margins.bottom() + 2 * frame_width)
        
        # Clamp to min/max constraints
        new_height = max(self._min_height, min(total_height, self.MAX_HEIGHT))
        
        # Update scrollbar policy based on whether we're at max height
        if total_height > self.MAX_HEIGHT:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Update height
        if self.height() != new_height:
            self.setFixedHeight(new_height)

    def set_send_sequence(self, sequence: str) -> None:
        """Update the shortcut used to send messages."""
        self._send_sequence = QKeySequence(sequence) if sequence else QKeySequence()
        self._update_placeholder()

    def _update_placeholder(self) -> None:
        sequence_text = self._send_sequence.toString() or "Ctrl+Return"
        self.setPlaceholderText(f"Type your message... ({sequence_text} to send)")
    
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events.
        
        Args:
            event: The key event.
        """
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
    
    sidebar_toggle_requested = Signal()  # Signal to toggle sidebar visibility
    memory_panel_requested = Signal()  # Signal to toggle memory panel visibility
    
    def __init__(
        self,
        viewmodel: ChatViewModel,
        settings_viewmodel: Optional["SettingsViewModel"] = None,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the chat panel.
        
        Args:
            viewmodel: The chat viewmodel.
            settings_viewmodel: Optional settings viewmodel for shortcuts.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.viewmodel = viewmodel
        self._settings_viewmodel = settings_viewmodel
        self.setObjectName("chatPanel")
        self._streaming_bubble: Optional[StreamingMessageBubble] = None
        self._message_widgets: list = []  # Track message bubble widgets
        self._is_prepending = False  # Flag to skip animation on prepends
        self._setup_ui()
        self._connect_signals()
        self._apply_send_shortcut()
        self._refresh_agents()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header with Amadeus Branding and Agent Selector
        header = QFrame()
        header.setFixedHeight(64)
        header.setObjectName("chatHeader")
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 0, 24, 0)
        header_layout.setSpacing(12)
        
        # Left Spacer - REMOVED for Left Alignment
        # header_layout.addStretch()

        # Title/Subtitle Container
        # Explicitly transparent to avoid background block issues
        title_container = QWidget()
        title_container.setStyleSheet("background-color: transparent;")
        title_layout_v = QVBoxLayout(title_container)
        title_layout_v.setContentsMargins(0, 0, 0, 0)
        title_layout_v.setSpacing(2)
        title_layout_v.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Title Row
        title_row = QWidget()
        title_row.setStyleSheet("background-color: transparent;")
        title_row_layout = QHBoxLayout(title_row)
        title_row_layout.setContentsMargins(0, 0, 0, 0)
        title_row_layout.setSpacing(8)
        title_row_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Status Pulse
        status_dot = QFrame()
        status_dot.setFixedSize(8, 8)
        status_dot.setStyleSheet("background-color: #00C2FF; border-radius: 4px;")
        title_row_layout.addWidget(status_dot)
        
        # Title
        self._header_label = QLabel("AMADEUS CHANNEL")
        self._header_label.setObjectName("headerLabel")
        title_row_layout.addWidget(self._header_label)
        
        title_layout_v.addWidget(title_row)

        # Subtitle
        subtitle = QLabel("SECURE CONNECTION // AMADEUS PROTOCOL V1.02")
        subtitle.setStyleSheet("color: #6B7280; font-size: 8px; font-weight: bold; letter-spacing: 1.5px; background-color: transparent; padding-left: 16px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title_layout_v.addWidget(subtitle)

        header_layout.addWidget(title_container)
        
        # Spacer to push Agent Selector to right
        header_layout.addStretch()
        
        # Right Side - Agent Selector
        right_container = QWidget()
        right_container.setStyleSheet("background-color: transparent;")
        right_layout = QHBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        agent_label = QLabel("PROTOCOL:")
        agent_label.setStyleSheet("color: #6B7280; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        right_layout.addWidget(agent_label)
        
        self._agent_combo = QComboBox()
        self._agent_combo.setMinimumWidth(150)
        self._agent_combo.setToolTip("Select agent for this chat")
        self._agent_combo.setAccessibleName("Agent selector")
        self._agent_combo.setAccessibleDescription("Choose the AI agent to respond to your messages")
        self._agent_combo.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        right_layout.addWidget(self._agent_combo)
        
        # Memory Button
        self._memory_btn = QPushButton("⛁ (0)")
        self._memory_btn.setObjectName("iconButton")
        self._memory_btn.setFixedSize(52, 32)
        self._memory_btn.setToolTip("Toggle memory panel")
        self._memory_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._memory_btn.clicked.connect(self.memory_panel_requested.emit)
        right_layout.addWidget(self._memory_btn)
        
        # Sidebar Toggle Button
        self._sidebar_toggle_btn = QPushButton("☰")
        self._sidebar_toggle_btn.setObjectName("iconButton")
        self._sidebar_toggle_btn.setFixedSize(32, 32)
        self._sidebar_toggle_btn.setToolTip("Toggle sidebar")
        self._sidebar_toggle_btn.setStyleSheet("font-size: 16px; font-weight: bold; outline: none; border: none;")
        self._sidebar_toggle_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._sidebar_toggle_btn.clicked.connect(self.sidebar_toggle_requested.emit)
        right_layout.addWidget(self._sidebar_toggle_btn)
        
        header_layout.addWidget(right_container)
        
        layout.addWidget(header)
        
        # Messages area
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        
        self._messages_container = QWidget()
        self._messages_layout = QVBoxLayout(self._messages_container)
        self._messages_layout.setContentsMargins(0, 20, 0, 20)
        self._messages_layout.setSpacing(16)
        
        # History loading spinner/button at top
        self._history_loader = QPushButton("Load older messages...")
        self._history_loader.setObjectName("historyLoader")
        self._history_loader.setVisible(False)
        self._history_loader.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 194, 255, 0.15);
                color: #00C2FF;
                border: 1px dashed rgba(0, 194, 255, 0.4);
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(0, 194, 255, 0.25);
            }
            QPushButton:disabled {
                color: #6B7280;
                border-color: #6B7280;
            }
        """)
        self._history_loader.clicked.connect(self._on_load_history_clicked)
        self._messages_layout.addWidget(self._history_loader)
        
        self._messages_layout.addStretch()
        
        self._scroll_area.setWidget(self._messages_container)
        layout.addWidget(self._scroll_area, 1)
        
        # Enable smooth scrolling with QScroller for touch/gesture scrolling
        QScroller.grabGesture(
            self._scroll_area.viewport(),
            QScroller.ScrollerGestureType.LeftMouseButtonGesture,
        )
        
        # Animation for programmatic scroll-to-bottom
        self._scroll_animation = QPropertyAnimation()
        self._scroll_animation.setDuration(200)
        self._scroll_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Connect scroll bar for auto-load on scroll to top
        self._scroll_area.verticalScrollBar().valueChanged.connect(
            self._on_scroll_changed
        )
        
        # Bottom Area
        bottom_container = QWidget()
        # bottom_container.setStyleSheet("background-color: #181B21; border-top: 1px solid #2D3340;") # Background matching design footer
        # Actually in design: "bg-surface-light dark:bg-surface-dark border-t..."
        # So we should style this container.
        
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(20, 20, 20, 20)
        bottom_layout.setSpacing(10)
        
        # Input Wrapper (The floating box)
        input_wrapper = QFrame()
        input_wrapper.setObjectName("inputArea")
        input_inner_layout = QHBoxLayout(input_wrapper)
        input_inner_layout.setContentsMargins(8, 8, 8, 8)
        input_inner_layout.setSpacing(10)
        
        # Add Button (Plus)
        self._add_btn = QPushButton("+")
        self._add_btn.setObjectName("iconButton")
        self._add_btn.setFixedSize(32, 32)
        self._add_btn.setAccessibleName("Add attachment")
        self._add_btn.setAccessibleDescription("Add an image or file attachment to the message")
        self._add_btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        input_inner_layout.addWidget(self._add_btn)
        
        # Text Input
        self._message_input = MessageInput()
        self._message_input.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        # Remove border/bg from the actual input widget since the wrapper handles the look
        self._message_input.setStyleSheet(
            "background: transparent; border: none; padding: 0px;"
        )
        self._message_input.setAccessibleName("Message input")
        self._message_input.setAccessibleDescription("Type your message here")
        self._message_input.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        input_inner_layout.addWidget(
            self._message_input, 1, Qt.AlignmentFlag.AlignVCenter
        )
        
        # Send Button
        self._send_btn = QPushButton("➤") # Using arrow symbol
        self._send_btn.setFixedSize(32, 32)
        self._send_btn.setStyleSheet("""
            QPushButton {
                background-color: #00C2FF;
                color: white;
                border-radius: 8px;
                font-size: 13px;
                padding: 0px;
                padding-bottom: 2px;
                margin: 0px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #009ACD;
            }
        """)
        self._send_btn.setAccessibleName("Send message")
        self._send_btn.setAccessibleDescription("Send the current message to the assistant")
        self._send_btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        input_inner_layout.addWidget(self._send_btn)
        
        # Cancel Button (replaces send when loading)
        self._cancel_btn = QPushButton("■")
        self._cancel_btn.setFixedSize(32, 32)
        self._cancel_btn.setVisible(False)
        self._cancel_btn.setStyleSheet("""
            QPushButton {
                 background-color: #EF4444;
                 color: white;
                 border-radius: 8px;
                 font-size: 13px;
                 padding: 0px;
                 padding-bottom: 2px;
                 margin: 0px;
            }
        """)
        self._cancel_btn.setAccessibleName("Cancel generation")
        self._cancel_btn.setAccessibleDescription("Stop the current response generation")
        self._cancel_btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        input_inner_layout.addWidget(self._cancel_btn)
        
        bottom_layout.addWidget(input_wrapper)
        
        # Attachment preview strip (hidden by default)
        self._attachment_strip = QWidget()
        self._attachment_strip.setVisible(False)
        self._attachment_strip.setAccessibleName("Pending attachments")
        attachment_strip_layout = QHBoxLayout(self._attachment_strip)
        attachment_strip_layout.setContentsMargins(8, 4, 8, 4)
        attachment_strip_layout.setSpacing(8)
        self._attachment_thumbnails = attachment_strip_layout
        attachment_strip_layout.addStretch()
        bottom_layout.insertWidget(0, self._attachment_strip)
        
        # Footer removed
        # footer_label removed as it moved to header
        
        layout.addWidget(bottom_container)
    
    def _connect_signals(self) -> None:
        """Connect signals to slots."""
        # ViewModel signals
        self.viewmodel.messages_changed.connect(self._refresh_messages)
        self.viewmodel.is_loading_changed.connect(self._on_loading_changed)
        self.viewmodel.streaming_content_changed.connect(
            self._on_streaming_content
        )
        self.viewmodel.current_chat_changed.connect(self._on_chat_changed)
        self.viewmodel.available_agents_changed.connect(self._refresh_agents)
        self.viewmodel.current_agent_changed.connect(self._on_agent_changed)
        
        # Paging signals
        self.viewmodel.history_loading_changed.connect(self._on_history_loading_changed)
        self.viewmodel.messages_prepended.connect(self._on_messages_prepended)
        
        # UI signals
        self._message_input.send_requested.connect(self._send_message)
        self._send_btn.clicked.connect(self._send_message)
        self._cancel_btn.clicked.connect(self.viewmodel.cancel_generation)
        self._agent_combo.currentIndexChanged.connect(self._on_agent_combo_changed)
        
        # Connect pending attachments signal
        self.viewmodel.pending_attachments_changed.connect(self._refresh_attachment_strip)

        if self._settings_viewmodel:
            self._settings_viewmodel.settings_changed.connect(
                self._apply_send_shortcut
            )
    
    def _refresh_agents(self) -> None:
        """Refresh the agent dropdown."""
        self._agent_combo.blockSignals(True)
        self._agent_combo.clear()
        
        for agent in self.viewmodel.available_agents:
            self._agent_combo.addItem(agent.name, agent.id)
        
        # Select current agent
        current = self.viewmodel.current_agent
        if current:
            index = self._agent_combo.findData(current.id)
            if index >= 0:
                self._agent_combo.setCurrentIndex(index)
        
        self._agent_combo.blockSignals(False)
    
    def _on_agent_changed(self) -> None:
        """Handle agent change from viewmodel."""
        current = self.viewmodel.current_agent
        if current:
            index = self._agent_combo.findData(current.id)
            if index >= 0:
                self._agent_combo.blockSignals(True)
                self._agent_combo.setCurrentIndex(index)
                self._agent_combo.blockSignals(False)
    
    def _on_agent_combo_changed(self, index: int) -> None:
        """Handle agent selection change."""
        if index < 0:
            return
        agent_id = self._agent_combo.itemData(index)
        if agent_id:
            self.viewmodel.select_agent(agent_id)
    
    def _refresh_messages(self) -> None:
        """Refresh the messages display."""
        # Track count before refresh to detect appended messages
        old_count = len(self._message_widgets)
        
        # Clear tracked widgets
        self._message_widgets.clear()
        
        # Remove old messages (keep history loader at index 0 and stretch at end)
        while self._messages_layout.count() > 2:
            item = self._messages_layout.takeAt(1)  # Remove after history loader
            if item.widget():
                item.widget().deleteLater()
        
        # Get current agent name for display
        current_agent = self.viewmodel.current_agent
        agent_name = current_agent.name if current_agent else "Assistant"
        
        # Add messages
        new_count = len(self.viewmodel.messages)
        is_single_append = new_count == old_count + 1 and old_count > 0
        
        for i, message in enumerate(self.viewmodel.messages):
            attachments = self.viewmodel.get_message_attachments(message.id)
            bubble = MessageBubble(message, agent_name=agent_name, attachments=attachments)
            self._message_widgets.append(bubble)
            # Insert before the stretch (which is at count - 1)
            self._messages_layout.insertWidget(
                self._messages_layout.count() - 1, bubble
            )
            
            # Animate only the last (newly appended) message, not batch loads
            if is_single_append and i == new_count - 1 and not self._is_prepending:
                QTimer.singleShot(10, bubble.animate_in)
        
        # Update history loader visibility
        self._history_loader.setVisible(self.viewmodel.has_more_history)
        
        # Scroll to bottom
        QTimer.singleShot(50, self._scroll_to_bottom)
    
    def _on_scroll_changed(self, value: int) -> None:
        """Handle scroll position changes for auto-loading history."""
        # Check if scrolled near top and should load more
        if (
            value <= 50
            and self.viewmodel.has_more_history
            and not self.viewmodel.is_loading_history
        ):
            self.viewmodel.load_older_messages()
    
    def _on_load_history_clicked(self) -> None:
        """Handle manual history load button click."""
        if self.viewmodel.has_more_history:
            self.viewmodel.load_older_messages()
    
    def _on_history_loading_changed(self) -> None:
        """Handle history loading state change."""
        is_loading = self.viewmodel.is_loading_history
        self._history_loader.setEnabled(not is_loading)
        if is_loading:
            self._history_loader.setText("Loading...")
        else:
            self._history_loader.setText("Load older messages...")
            self._history_loader.setVisible(self.viewmodel.has_more_history)
    
    def _on_messages_prepended(self, count: int) -> None:
        """Handle prepending older messages with scroll position preservation.
        
        Args:
            count: Number of messages that were prepended.
        """
        if count <= 0:
            return
        
        # Store current scroll position relative to content
        scrollbar = self._scroll_area.verticalScrollBar()
        old_max = scrollbar.maximum()
        old_value = scrollbar.value()
        
        # Get current agent name
        current_agent = self.viewmodel.current_agent
        agent_name = current_agent.name if current_agent else "Assistant"
        
        # Get the prepended messages (they are at the beginning of viewmodel.messages)
        prepended_messages = self.viewmodel.messages[:count]
        
        # Insert prepended message bubbles after the history loader (index 1)
        self._is_prepending = True
        for i, message in enumerate(prepended_messages):
            attachments = self.viewmodel.get_message_attachments(message.id)
            bubble = MessageBubble(message, agent_name=agent_name, attachments=attachments)
            self._message_widgets.insert(i, bubble)
            # Insert after history loader, at position 1 + i
            self._messages_layout.insertWidget(1 + i, bubble)
        self._is_prepending = False
        
        # Restore scroll position after layout update
        def restore_scroll():
            new_max = scrollbar.maximum()
            delta = new_max - old_max
            scrollbar.setValue(old_value + delta)
        
        QTimer.singleShot(10, restore_scroll)
    
    def _on_loading_changed(self) -> None:
        """Handle loading state change."""
        is_loading = self.viewmodel.is_loading
        
        self._send_btn.setVisible(not is_loading)
        self._cancel_btn.setVisible(is_loading)
        self._message_input.setEnabled(not is_loading)
        
        if is_loading:
            # Get current agent name
            current_agent = self.viewmodel.current_agent
            agent_name = current_agent.name if current_agent else "Assistant"
            
            # Add streaming bubble
            self._streaming_bubble = StreamingMessageBubble(agent_name=agent_name)
            self._messages_layout.insertWidget(
                self._messages_layout.count() - 1, self._streaming_bubble
            )
            self._scroll_to_bottom()
        else:
            # Remove streaming bubble
            if self._streaming_bubble:
                self._streaming_bubble.deleteLater()
                self._streaming_bubble = None
    
    def _on_streaming_content(self) -> None:
        """Handle streaming content update."""
        if self._streaming_bubble:
            self._streaming_bubble.set_content(self.viewmodel.streaming_content)
            self._scroll_to_bottom()
    
    def _on_chat_changed(self) -> None:
        """Handle chat change."""
        chat = self.viewmodel.current_chat
        if chat:
            # Assuming we want to show the chat title somewhere else or update the header?
            # Design shows "AMADEUS CHANNEL" constant.
            # We can perhaps append the chat title if needed, or just let it be generic.
            # Let's keep AMADEUS CHANNEL as the main branding, maybe show title in window title or subtitle.
            pass
        else:
            pass

    def _apply_send_shortcut(self) -> None:
        """Update the send shortcut based on settings."""
        sequence = "Ctrl+Return"
        if self._settings_viewmodel:
            for shortcut in self._settings_viewmodel.shortcuts:
                if shortcut.action == "send_message":
                    sequence = shortcut.key_sequence or sequence
                    break
        self._message_input.set_send_sequence(sequence)
    
    def _send_message(self) -> None:
        """Send the current message."""
        content = self._message_input.toPlainText()
        if content.strip():
            self.viewmodel.send_message(content)
            self._message_input.clear()
    
    def _scroll_to_bottom(self, animate: bool = True) -> None:
        """Scroll the message area to the bottom.
        
        Args:
            animate: If True, use smooth animation. If False, jump immediately.
        """
        scrollbar = self._scroll_area.verticalScrollBar()
        target = scrollbar.maximum()
        
        if not animate or self._is_prepending:
            scrollbar.setValue(target)
            return
        
        # Animated scroll
        self._scroll_animation.stop()
        self._scroll_animation.setTargetObject(scrollbar)
        self._scroll_animation.setPropertyName(b"value")
        self._scroll_animation.setStartValue(scrollbar.value())
        self._scroll_animation.setEndValue(target)
        self._scroll_animation.start()
    
    def focus_input(self) -> None:
        """Focus the message input."""
        self._message_input.setFocus()

    def _refresh_attachment_strip(self) -> None:
        """Refresh the attachment preview strip."""
        # Clear existing thumbnails
        while self._attachment_thumbnails.count() > 1:  # Keep the stretch
            item = self._attachment_thumbnails.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        attachments = self.viewmodel.pending_attachments
        
        if not attachments:
            self._attachment_strip.setVisible(False)
            return
        
        self._attachment_strip.setVisible(True)
        
        # Add thumbnail for each attachment
        for i, image in enumerate(attachments):
            thumb_container = QWidget()
            thumb_layout = QVBoxLayout(thumb_container)
            thumb_layout.setContentsMargins(0, 0, 0, 0)
            thumb_layout.setSpacing(2)
            
            # Create thumbnail label
            thumb_label = QLabel()
            thumb_label.setFixedSize(60, 60)
            thumb_label.setStyleSheet(
                "border: 2px solid #4285f4; border-radius: 4px; background: #2d2d2d;"
            )
            pixmap = QPixmap.fromImage(image)
            scaled = pixmap.scaled(
                56, 56,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            thumb_label.setPixmap(scaled)
            thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            thumb_layout.addWidget(thumb_label)
            
            # Remove button
            remove_btn = QPushButton("✕")
            remove_btn.setFixedSize(20, 20)
            remove_btn.setStyleSheet(
                "QPushButton { background: #EF4444; color: white; border-radius: 10px; font-size: 10px; }"
                "QPushButton:hover { background: #DC2626; }"
            )
            remove_btn.clicked.connect(lambda checked, idx=i: self._remove_attachment(idx))
            thumb_layout.addWidget(remove_btn, alignment=Qt.AlignmentFlag.AlignCenter)
            
            self._attachment_thumbnails.insertWidget(
                self._attachment_thumbnails.count() - 1, thumb_container
            )
    
    def _remove_attachment(self, index: int) -> None:
        """Remove an attachment by index."""
        self.viewmodel.remove_pending_attachment(index)

    def update_memory_count(self, count: int) -> None:
        """Update the memory button count label.
        
        Args:
            count: The number of memories to display.
        """
        self._memory_btn.setText(f"⛁ ({count})")
