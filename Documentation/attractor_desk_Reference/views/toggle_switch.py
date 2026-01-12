"""Custom toggle switch widget."""

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRect,
    Qt,
    Property,
    QPoint,
    QSize,
)
from PySide6.QtGui import QColor, QPainter, QPaintEvent
from PySide6.QtWidgets import QAbstractButton, QSizePolicy, QWidget


class ToggleSwitch(QAbstractButton):
    """A iOS-style toggle switch widget."""

    def __init__(self, parent: QWidget = None):
        """Initialize the toggle switch.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setCheckable(True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Colors
        self._track_color_off = QColor("#363a4f")  # Surface0/Overlay0 in Catppuccin
        self._track_color_on = QColor("#a6e3a1")   # Green
        self._thumb_color = QColor("#ffffff")      # White
        self._text_color = QColor("#cdd6f4")       # Text

        # Animation
        self._thumb_position = 0.0
        self._animation = QPropertyAnimation(self, b"thumb_position", self)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._animation.setDuration(200)  # ms

        self.toggled.connect(self._start_animation)

    def sizeHint(self) -> QSize:
        """Return the recommended size for the widget."""
        return QSize(50, 26)

    @Property(float)
    def thumb_position(self) -> float:
        """Get the current thumb position (0.0 to 1.0)."""
        return self._thumb_position

    @thumb_position.setter
    def thumb_position(self, pos: float) -> None:
        """Set the thumb position."""
        self._thumb_position = pos
        self.update()

    def _start_animation(self, checked: bool) -> None:
        """Start the slide animation."""
        self._animation.stop()
        self._animation.setStartValue(self._thumb_position)
        self._animation.setEndValue(1.0 if checked else 0.0)
        self._animation.start()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint the toggle switch."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        track_height = rect.height()
        thumb_size = track_height - 6
        
        # Draw track
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Interpolate color roughly
        if self._thumb_position > 0.5:
            painter.setBrush(self._track_color_on)
        else:
            painter.setBrush(self._track_color_off)
            
        # Or better: smooth color transition could be implemented, but simple is fine for now
        
        painter.drawRoundedRect(rect, track_height / 2, track_height / 2)

        # Draw thumb
        thumb_x = 3 + (rect.width() - thumb_size - 6) * self._thumb_position
        thumb_rect = QRect(
            int(thumb_x),
            3,
            thumb_size,
            thumb_size
        )
        
        painter.setBrush(self._thumb_color)
        painter.drawEllipse(thumb_rect)

    def hitButton(self, pos: QPoint) -> bool:
        """Check if the click was inside the widget."""
        return self.rect().contains(pos)
