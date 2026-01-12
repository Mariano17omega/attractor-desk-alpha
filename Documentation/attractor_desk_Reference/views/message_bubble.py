"""Message bubble widget for displaying chat messages with agent indicator."""

from pathlib import Path
from typing import Optional

import markdown

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
from PySide6.QtGui import QImage, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..core.models import Message, MessageRole

# Animation constants
MESSAGE_ANIMATION_DURATION = 200  # ms

AVATAR_SIZE = 40
PROFILE_DIR = Path(__file__).resolve().parents[1] / "assets" / "profile"
USER_AVATAR_FILE = "use.png"
DEFAULT_AGENT_AVATAR = "kurisu.jpeg"
AGENT_AVATAR_MAP = {
    "faris": "faris.png",
    "itaru": "itaru.png",
    "kurisu": "kurisu.jpeg",
    "maho": "maho.png",
    "suzuha": "suzuha.png",
}


def _fallback_avatar_text(agent_name: str, is_user: bool) -> str:
    if is_user:
        return "U"
    cleaned = agent_name.strip()
    return cleaned[:1].upper() if cleaned else "A"


def _find_avatar_file(name: str) -> Optional[Path]:
    if not name:
        return None
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        candidate = PROFILE_DIR / f"{name}{ext}"
        if candidate.exists():
            return candidate
    return None


def _resolve_avatar_path(agent_name: str, is_user: bool) -> Optional[Path]:
    if is_user:
        candidate = PROFILE_DIR / USER_AVATAR_FILE
        return candidate if candidate.exists() else None

    normalized = agent_name.strip().lower()
    mapped = AGENT_AVATAR_MAP.get(normalized)
    if mapped:
        candidate = PROFILE_DIR / mapped
        if candidate.exists():
            return candidate

    candidate = _find_avatar_file(normalized)
    if candidate:
        return candidate

    fallback = PROFILE_DIR / DEFAULT_AGENT_AVATAR
    return fallback if fallback.exists() else None


def _circle_pixmap(path: Path, size: int) -> QPixmap:
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return QPixmap()

    scaled = pixmap.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    x_offset = max(0, (scaled.width() - size) // 2)
    y_offset = max(0, (scaled.height() - size) // 2)
    cropped = scaled.copy(x_offset, y_offset, size, size)

    result = QPixmap(size, size)
    result.fill(Qt.GlobalColor.transparent)

    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    clip_path = QPainterPath()
    clip_path.addEllipse(0, 0, size, size)
    painter.setClipPath(clip_path)
    painter.drawPixmap(0, 0, cropped)
    painter.end()

    return result


def _create_avatar_label(agent_name: str, is_user: bool) -> QLabel:
    label = QLabel()
    label.setFixedSize(AVATAR_SIZE, AVATAR_SIZE)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setObjectName("userAvatar" if is_user else "assistantAvatar")

    avatar_path = _resolve_avatar_path(agent_name, is_user)
    if avatar_path:
        pixmap = _circle_pixmap(avatar_path, AVATAR_SIZE)
        if not pixmap.isNull():
            label.setPixmap(pixmap)
            return label

    label.setText(_fallback_avatar_text(agent_name, is_user))
    return label


class MessageBubble(QFrame):
    """Widget for displaying a single message in the chat."""
    
    def __init__(
        self,
        message: Message,
        agent_name: str = "Assistant",
        attachments: list = None,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the message bubble.
        
        Args:
            message: The message to display.
            agent_name: Name of the agent for assistant messages.
            attachments: Optional list of QImage attachments.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.message = message
        self.agent_name = agent_name
        self.attachments = attachments or []
        self._animation_group: Optional[QParallelAnimationGroup] = None
        self._setup_ui()
        
        # Add accessible name for screen readers
        role_name = "Your message" if message.role == MessageRole.USER else f"Message from {agent_name}"
        self.setAccessibleName(role_name)
        self.setAccessibleDescription(message.content[:100] if message.content else "")
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        is_user = self.message.role == MessageRole.USER
        
        # Set object name for styling
        self.setObjectName("messageRow")
        
        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 6, 10, 6)
        main_layout.setSpacing(12)
        
        avatar_label = _create_avatar_label(self.agent_name, is_user)

        # Create bubble content
        bubble = QFrame()
        bubble.setObjectName("userMessage" if is_user else "assistantMessage")
        bubble.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)
        bubble.setMaximumWidth(600)
        
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(12, 8, 12, 8)
        bubble_layout.setSpacing(4)
        
        # Role label for assistant messages (shows agent name)
        if not is_user:
            role_label = QLabel(self.agent_name)
            # We use a generic style or rely on parent, but let's give it a specific ID if we want specific styling
            # Or just set a style that leverages the defined theme colors
            # Using inline style for now to ensure it looks right without a specific ID in styles.py yet
            # role_label.setStyleSheet("font-size: 11px; font-weight: bold; opacity: 0.7;") 
            # Better to use objectName
            role_label.setObjectName("roleLabel")
            role_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #9CA3AF;")
            bubble_layout.addWidget(role_label)
        
        # Message content - render as markdown
        content_label = QLabel()
        content_label.setWordWrap(True)
        content_label.setTextFormat(Qt.TextFormat.RichText)
        content_label.setOpenExternalLinks(True)
        content_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        content_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        # Convert markdown to HTML
        html_content = markdown.markdown(
            self.message.content or "",
            extensions=['fenced_code', 'tables', 'nl2br']
        )
        content_label.setText(html_content)
        bubble_layout.addWidget(content_label)
        
        # Display attachments as thumbnails
        if self.attachments:
            attachments_row = QWidget()
            attachments_layout = QHBoxLayout(attachments_row)
            attachments_layout.setContentsMargins(0, 8, 0, 0)
            attachments_layout.setSpacing(8)
            
            for image in self.attachments:
                thumb_label = QLabel()
                thumb_label.setFixedSize(80, 80)
                thumb_label.setStyleSheet(
                    "border: 2px solid #4285f4; border-radius: 4px; background: #2d2d2d;"
                )
                pixmap = QPixmap.fromImage(image)
                scaled = pixmap.scaled(
                    76, 76,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                thumb_label.setPixmap(scaled)
                thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                attachments_layout.addWidget(thumb_label)
            
            attachments_layout.addStretch()
            bubble_layout.addWidget(attachments_row)
        
        # Alignment
        if is_user:
            main_layout.addStretch()
            main_layout.addWidget(bubble, 0, Qt.AlignmentFlag.AlignTop)
            main_layout.addWidget(avatar_label, 0, Qt.AlignmentFlag.AlignTop)
        else:
            main_layout.addWidget(avatar_label, 0, Qt.AlignmentFlag.AlignTop)
            main_layout.addWidget(bubble, 0, Qt.AlignmentFlag.AlignTop)
            main_layout.addStretch()
        
        self.setLayout(main_layout)
    
    def animate_in(self) -> None:
        """Animate the message appearing with fade + subtle slide."""
        # Create opacity effect
        opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(opacity_effect)
        opacity_effect.setOpacity(0.0)
        
        # Fade animation
        fade_anim = QPropertyAnimation(opacity_effect, b"opacity", self)
        fade_anim.setDuration(MESSAGE_ANIMATION_DURATION)
        fade_anim.setStartValue(0.0)
        fade_anim.setEndValue(1.0)
        fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Slide animation (subtle vertical offset)
        self._original_pos = self.pos()
        slide_anim = QPropertyAnimation(self, b"pos", self)
        slide_anim.setDuration(MESSAGE_ANIMATION_DURATION)
        start_pos = self.pos()
        start_pos.setY(start_pos.y() + 10)  # Start 10px lower
        slide_anim.setStartValue(start_pos)
        slide_anim.setEndValue(self._original_pos)
        slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Run in parallel
        self._animation_group = QParallelAnimationGroup(self)
        self._animation_group.addAnimation(fade_anim)
        self._animation_group.addAnimation(slide_anim)
        self._animation_group.start()



class StreamingMessageBubble(QFrame):
    """Widget for displaying a streaming assistant message."""
    
    def __init__(
        self,
        agent_name: str = "Assistant",
        parent: Optional[QWidget] = None,
    ):
        """Initialize the streaming message bubble.
        
        Args:
            agent_name: Name of the agent for the response.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._content = ""
        self.agent_name = agent_name
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        self.setObjectName("messageRow")
        
        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 6, 10, 6)
        main_layout.setSpacing(12)
        
        avatar_label = _create_avatar_label(self.agent_name, False)

        # Create bubble content
        self._bubble = QFrame()
        self._bubble.setObjectName("assistantMessage")
        self._bubble.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum
        )
        self._bubble.setMaximumWidth(600)
        
        bubble_layout = QVBoxLayout(self._bubble)
        bubble_layout.setContentsMargins(12, 8, 12, 8)
        bubble_layout.setSpacing(4)
        
        # Role label (shows agent name)
        role_label = QLabel(self.agent_name)
        role_label.setObjectName("roleLabel")
        role_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #9CA3AF;")
        bubble_layout.addWidget(role_label)
        
        # Message content - render as markdown
        self._content_label = QLabel("...")
        self._content_label.setWordWrap(True)
        self._content_label.setTextFormat(Qt.TextFormat.RichText)
        self._content_label.setOpenExternalLinks(True)
        self._content_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self._content_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        bubble_layout.addWidget(self._content_label)
        
        main_layout.addWidget(avatar_label, 0, Qt.AlignmentFlag.AlignTop)
        main_layout.addWidget(self._bubble, 0, Qt.AlignmentFlag.AlignTop)
        main_layout.addStretch()
        
        self.setLayout(main_layout)
    
    def set_content(self, content: str) -> None:
        """Update the displayed content.
        
        Args:
            content: The content to display.
        """
        self._content = content
        if content:
            html_content = markdown.markdown(
                content,
                extensions=['fenced_code', 'tables', 'nl2br']
            )
            self._content_label.setText(html_content)
        else:
            self._content_label.setText("...")
