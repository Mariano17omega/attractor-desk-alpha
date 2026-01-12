"""Screen region selection overlay widget."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class RegionSelectionOverlay(QWidget):
    """Full-screen overlay for selecting a capture region."""

    selection_made = Signal(QRect)
    cancelled = Signal()

    def __init__(self, screen_geometry: QRect, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setGeometry(screen_geometry)
        self._origin: Optional[QPoint] = None
        self._current_rect = QRect()

    def showEvent(self, event) -> None:
        self.setCursor(Qt.CursorShape.CrossCursor)
        super().showEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.position().toPoint()
            self._current_rect = QRect(self._origin, self._origin)
            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._origin is not None:
            current = event.position().toPoint()
            self._current_rect = QRect(self._origin, current)
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._origin is not None:
            selection = self._current_rect.normalized()
            self._origin = None
            if selection.width() > 0 and selection.height() > 0:
                global_rect = selection.translated(self.geometry().topLeft())
                self.selection_made.emit(global_rect)
            self.close()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            self.close()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 140))
        if not self._current_rect.isNull():
            pen = QPen(QColor(0, 194, 255), 2)
            painter.setPen(pen)
            painter.drawRect(self._current_rect.normalized())
        painter.end()
