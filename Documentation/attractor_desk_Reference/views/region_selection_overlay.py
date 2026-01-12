"""Region selection overlay widget for screen capture."""

from typing import Optional

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QKeyEvent, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget


class RegionSelectionOverlay(QWidget):
    """Full-screen overlay for selecting a screen region via drag."""

    # Signals
    region_selected = Signal(QRect)
    selection_cancelled = Signal()

    def __init__(self, monitor_geometry: QRect, parent: Optional[QWidget] = None):
        """Initialize the region selection overlay.

        Args:
            monitor_geometry: The geometry of the monitor to overlay.
            parent: Parent widget.
        """
        super().__init__(parent)

        self._monitor_geometry = monitor_geometry
        self._start_pos: Optional[QPoint] = None
        self._current_pos: Optional[QPoint] = None
        self._is_selecting = False

        self._setup_overlay()
        
        # Accessibility
        self.setAccessibleName("Screen region selector")
        self.setAccessibleDescription("Click and drag to select a region. Press Escape to cancel.")

    def _setup_overlay(self) -> None:
        """Set up the overlay window properties."""
        # Frameless, stay on top, tool window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.BypassWindowManagerHint
        )
        
        # Set window attributes
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        # Position and size to match monitor
        self.setGeometry(self._monitor_geometry)
        
        # Set crosshair cursor
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        
        # Enable mouse tracking
        self.setMouseTracking(True)

    def paintEvent(self, event) -> None:
        """Paint the overlay with selection visualization."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Semi-transparent dark overlay
        overlay_color = QColor(0, 0, 0, 120)
        painter.fillRect(self.rect(), overlay_color)

        # Draw selection rectangle if selecting
        if self._start_pos and self._current_pos and self._is_selecting:
            selection = self._get_selection_rect()
            
            # Clear the selection area (make it transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(selection, Qt.GlobalColor.transparent)
            
            # Draw border around selection
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            pen = QPen(QColor(66, 133, 244))  # Blue border
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(selection)

            # Draw dimension label
            self._draw_dimensions(painter, selection)

        # Draw crosshair at cursor if not yet selecting
        if not self._is_selecting:
            self._draw_crosshair(painter)

        # Draw instructions
        self._draw_instructions(painter)

    def _get_selection_rect(self) -> QRect:
        """Get the normalized selection rectangle."""
        if not self._start_pos or not self._current_pos:
            return QRect()

        # Normalize the rectangle (handle any drag direction)
        x1, y1 = self._start_pos.x(), self._start_pos.y()
        x2, y2 = self._current_pos.x(), self._current_pos.y()

        left = min(x1, x2)
        top = min(y1, y2)
        width = abs(x2 - x1)
        height = abs(y2 - y1)

        return QRect(left, top, width, height)

    def _draw_crosshair(self, painter: QPainter) -> None:
        """Draw a crosshair at the current cursor position."""
        cursor_pos = self.mapFromGlobal(QCursor.pos())
        
        pen = QPen(QColor(255, 255, 255, 180))
        pen.setWidth(1)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)

        # Horizontal line
        painter.drawLine(0, cursor_pos.y(), self.width(), cursor_pos.y())
        # Vertical line
        painter.drawLine(cursor_pos.x(), 0, cursor_pos.x(), self.height())

    def _draw_dimensions(self, painter: QPainter, rect: QRect) -> None:
        """Draw dimension label for the selection."""
        text = f"{rect.width()} × {rect.height()}"
        
        font = painter.font()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        
        # Position label below the selection
        text_rect = painter.fontMetrics().boundingRect(text)
        label_x = rect.center().x() - text_rect.width() // 2
        label_y = rect.bottom() + 20
        
        # Keep label on screen
        if label_y + text_rect.height() > self.height():
            label_y = rect.top() - 20

        # Background for text
        bg_rect = QRect(
            label_x - 5,
            label_y - text_rect.height() - 2,
            text_rect.width() + 10,
            text_rect.height() + 6,
        )
        painter.fillRect(bg_rect, QColor(0, 0, 0, 180))
        
        # Draw text
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(label_x, label_y, text)

    def _draw_instructions(self, painter: QPainter) -> None:
        """Draw instructions at the top of the overlay."""
        text = "Click and drag to select region | Press ESC to cancel"
        
        font = painter.font()
        font.setPointSize(12)
        painter.setFont(font)
        
        text_rect = painter.fontMetrics().boundingRect(text)
        x = (self.width() - text_rect.width()) // 2
        y = 40
        
        # Background
        bg_rect = QRect(x - 10, y - text_rect.height() - 5, text_rect.width() + 20, text_rect.height() + 10)
        painter.fillRect(bg_rect, QColor(0, 0, 0, 200))
        
        # Text
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(x, y, text)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press to start selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_pos = event.pos()
            self._current_pos = event.pos()
            self._is_selecting = True
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move to update selection."""
        if self._is_selecting:
            self._current_pos = event.pos()
            self.update()
        else:
            # Update crosshair
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release to complete selection."""
        if event.button() == Qt.MouseButton.LeftButton and self._is_selecting:
            self._current_pos = event.pos()
            selection = self._get_selection_rect()
            
            # Hide immediately before any signal handling
            self.hide()
            
            # Only emit if selection has meaningful size
            if selection.width() > 5 and selection.height() > 5:
                # Convert to global screen coordinates
                global_rect = QRect(
                    self.mapToGlobal(selection.topLeft()),
                    selection.size(),
                )
                # Close and emit after hiding
                self.close()
                self.region_selected.emit(global_rect)
            else:
                self.close()
                self.selection_cancelled.emit()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events."""
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            self.close()
            self.selection_cancelled.emit()
        else:
            super().keyPressEvent(event)

    def showEvent(self, event) -> None:
        """Handle show event."""
        super().showEvent(event)
        # Ensure we have focus for keyboard events
        self.setFocus()
        self.activateWindow()
        self.raise_()
