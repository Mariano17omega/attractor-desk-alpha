"""Screen capture service using mss for cross-platform screen grabbing."""

import logging
from typing import Dict, Optional, Tuple

from PySide6.QtCore import QObject, QPoint, QRect, Signal
from PySide6.QtGui import QCursor, QGuiApplication, QImage

logger = logging.getLogger(__name__)


class ScreenCaptureService(QObject):
    """Service for capturing screen content using mss."""

    # Signals
    capture_started = Signal()
    capture_completed = Signal(QImage)
    capture_cancelled = Signal()
    capture_error = Signal(str)

    def __init__(self, parent: Optional[QObject] = None):
        """Initialize the screen capture service.

        Args:
            parent: Parent QObject.
        """
        super().__init__(parent)
        self._mss = None

    def _get_mss(self):
        """Get or create the mss instance (lazy initialization)."""
        if self._mss is None:
            try:
                import mss
                self._mss = mss.mss()
            except ImportError:
                logger.error("mss library not available")
                self.capture_error.emit("Screen capture library (mss) not installed")
                return None
            except Exception as e:
                logger.error(f"Failed to initialize mss: {e}")
                self.capture_error.emit(f"Failed to initialize screen capture: {e}")
                return None
        return self._mss

    def get_cursor_monitor(self) -> Optional[Dict]:
        """Get the monitor that contains the cursor.

        Returns:
            Monitor dict with 'left', 'top', 'width', 'height', 'index' keys,
            or None if detection fails.
        """
        sct = self._get_mss()
        if sct is None:
            return None

        try:
            cursor_pos = QCursor.pos()
            cursor_x, cursor_y = cursor_pos.x(), cursor_pos.y()

            # Find monitor containing cursor
            for i, monitor in enumerate(sct.monitors[1:], start=1):  # Skip combined monitor at index 0
                left = monitor["left"]
                top = monitor["top"]
                right = left + monitor["width"]
                bottom = top + monitor["height"]

                if left <= cursor_x < right and top <= cursor_y < bottom:
                    return {
                        "left": left,
                        "top": top,
                        "width": monitor["width"],
                        "height": monitor["height"],
                        "index": i,
                    }

            # Fallback to primary monitor
            if len(sct.monitors) > 1:
                primary = sct.monitors[1]
                return {
                    "left": primary["left"],
                    "top": primary["top"],
                    "width": primary["width"],
                    "height": primary["height"],
                    "index": 1,
                }

        except Exception as e:
            logger.error(f"Failed to detect cursor monitor: {e}")
            self.capture_error.emit(f"Failed to detect monitor: {e}")

        return None

    def capture_full_screen(self) -> Optional[QImage]:
        """Capture the entire monitor that contains the cursor.

        Returns:
            QImage of the captured screen, or None if capture fails.
        """
        self.capture_started.emit()

        monitor = self.get_cursor_monitor()
        if monitor is None:
            self.capture_error.emit("Could not determine active monitor")
            return None

        sct = self._get_mss()
        if sct is None:
            return None

        try:
            # Capture the monitor
            screenshot = sct.grab(monitor)
            
            # Convert to QImage (mss returns BGRA format)
            image = QImage(
                screenshot.rgb,
                screenshot.width,
                screenshot.height,
                screenshot.width * 3,  # RGB is 3 bytes per pixel
                QImage.Format.Format_RGB888,
            )
            
            # Make a copy since the original data is tied to mss buffer
            image = image.copy()
            
            self.capture_completed.emit(image)
            return image

        except Exception as e:
            logger.error(f"Screen capture failed: {e}")
            self.capture_error.emit(f"Screen capture failed: {e}")
            return None

    def capture_region(self, rect: QRect) -> Optional[QImage]:
        """Capture a specific region of the screen.

        Args:
            rect: The rectangle region to capture in screen coordinates.

        Returns:
            QImage of the captured region, or None if capture fails.
        """
        self.capture_started.emit()

        sct = self._get_mss()
        if sct is None:
            return None

        if rect.isEmpty():
            self.capture_error.emit("Invalid capture region")
            return None

        try:
            # Create monitor dict from rect
            region = {
                "left": rect.x(),
                "top": rect.y(),
                "width": rect.width(),
                "height": rect.height(),
            }

            # Capture the region
            screenshot = sct.grab(region)
            
            # Convert to QImage (mss returns BGRA format for grab with region)
            image = QImage(
                screenshot.rgb,
                screenshot.width,
                screenshot.height,
                screenshot.width * 3,  # RGB is 3 bytes per pixel
                QImage.Format.Format_RGB888,
            )
            
            # Make a copy since the original data is tied to mss buffer
            image = image.copy()
            
            self.capture_completed.emit(image)
            return image

        except Exception as e:
            logger.error(f"Region capture failed: {e}")
            self.capture_error.emit(f"Region capture failed: {e}")
            return None

    def get_monitor_geometry(self) -> Optional[QRect]:
        """Get the geometry of the monitor containing the cursor.

        Returns:
            QRect representing the monitor bounds, or None if detection fails.
        """
        monitor = self.get_cursor_monitor()
        if monitor:
            return QRect(
                monitor["left"],
                monitor["top"],
                monitor["width"],
                monitor["height"],
            )
        return None

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._mss is not None:
            try:
                self._mss.close()
            except Exception:
                pass
            self._mss = None
