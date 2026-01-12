"""Capture preview dialog for reviewing and editing screenshots."""

from typing import Optional

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QImage, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRubberBand,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class ImageViewer(QLabel):
    """Scrollable image viewer with crop selection support."""

    crop_selected = Signal(QRect)

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the image viewer.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._image: Optional[QImage] = None
        self._scale_factor = 1.0
        self._crop_enabled = False
        self._rubberband: Optional[QRubberBand] = None
        self._rubberband_origin: Optional[QPoint] = None

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(200, 200)
        self.setStyleSheet("background-color: #2d2d2d;")

    def set_image(self, image: QImage) -> None:
        """Set the image to display.

        Args:
            image: The QImage to display.
        """
        self._image = image
        self._update_display()

    def get_image(self) -> Optional[QImage]:
        """Get the current image."""
        return self._image

    def _update_display(self) -> None:
        """Update the displayed pixmap."""
        if self._image is None:
            self.clear()
            return

        # Scale image
        scaled_width = int(self._image.width() * self._scale_factor)
        scaled_height = int(self._image.height() * self._scale_factor)

        pixmap = QPixmap.fromImage(self._image)
        scaled_pixmap = pixmap.scaled(
            scaled_width,
            scaled_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled_pixmap)
        self.adjustSize()

    def zoom_in(self) -> None:
        """Zoom in by 25%."""
        self._scale_factor = min(4.0, self._scale_factor * 1.25)
        self._update_display()

    def zoom_out(self) -> None:
        """Zoom out by 25%."""
        self._scale_factor = max(0.25, self._scale_factor / 1.25)
        self._update_display()

    def reset_zoom(self) -> None:
        """Reset zoom to 100%."""
        self._scale_factor = 1.0
        self._update_display()

    def fit_to_window(self, width: int, height: int) -> None:
        """Fit image to the given dimensions.

        Args:
            width: Available width.
            height: Available height.
        """
        if self._image is None:
            return

        # Calculate scale to fit
        width_ratio = width / self._image.width()
        height_ratio = height / self._image.height()
        self._scale_factor = min(width_ratio, height_ratio, 1.0)
        self._update_display()

    def enable_crop(self, enabled: bool) -> None:
        """Enable or disable crop mode.

        Args:
            enabled: Whether crop mode is enabled.
        """
        self._crop_enabled = enabled
        if enabled:
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            if self._rubberband:
                self._rubberband.hide()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press for crop selection."""
        if self._crop_enabled and event.button() == Qt.MouseButton.LeftButton:
            self._rubberband_origin = event.pos()
            if self._rubberband is None:
                self._rubberband = QRubberBand(QRubberBand.Shape.Rectangle, self)
            self._rubberband.setGeometry(QRect(self._rubberband_origin, self._rubberband_origin))
            self._rubberband.show()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move for crop selection."""
        if self._crop_enabled and self._rubberband and self._rubberband_origin:
            self._rubberband.setGeometry(
                QRect(self._rubberband_origin, event.pos()).normalized()
            )
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release for crop selection."""
        if self._crop_enabled and self._rubberband and self._rubberband_origin:
            crop_rect = self._rubberband.geometry()
            self._rubberband.hide()
            self._rubberband_origin = None

            # Convert to image coordinates
            if crop_rect.width() > 10 and crop_rect.height() > 10:
                pixmap = self.pixmap()
                if pixmap:
                    # Calculate offset from label to pixmap
                    pixmap_rect = self._get_pixmap_rect()
                    if pixmap_rect:
                        # Adjust crop rect relative to pixmap
                        adjusted_rect = QRect(
                            crop_rect.x() - pixmap_rect.x(),
                            crop_rect.y() - pixmap_rect.y(),
                            crop_rect.width(),
                            crop_rect.height(),
                        )
                        # Scale to original image coordinates
                        image_rect = QRect(
                            int(adjusted_rect.x() / self._scale_factor),
                            int(adjusted_rect.y() / self._scale_factor),
                            int(adjusted_rect.width() / self._scale_factor),
                            int(adjusted_rect.height() / self._scale_factor),
                        )
                        self.crop_selected.emit(image_rect)
        else:
            super().mouseReleaseEvent(event)

    def _get_pixmap_rect(self) -> Optional[QRect]:
        """Get the rect where the pixmap is actually drawn within the label."""
        pixmap = self.pixmap()
        if pixmap is None:
            return None

        label_size = self.size()
        pixmap_size = pixmap.size()

        x = (label_size.width() - pixmap_size.width()) // 2
        y = (label_size.height() - pixmap_size.height()) // 2

        return QRect(x, y, pixmap_size.width(), pixmap_size.height())


class CapturePreviewDialog(QDialog):
    """Dialog for previewing and editing a captured screenshot."""

    # Signals
    retake_requested = Signal()

    def __init__(
        self,
        image: QImage,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the capture preview dialog.

        Args:
            image: The captured image to preview.
            parent: Parent widget.
        """
        super().__init__(parent)

        self._original_image = image.copy()
        self._current_image = image.copy()
        self._crop_mode = False

        self._setup_ui()
        self._connect_signals()
        self._update_preview()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Capture Preview")
        self.setMinimumSize(600, 500)
        self.resize(800, 600)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Scroll area for image
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #2d2d2d; }")
        self._scroll_area.setAccessibleName("Capture preview area")

        self._image_viewer = ImageViewer()
        self._image_viewer.setAccessibleName("Captured image")
        self._image_viewer.setAccessibleDescription("Preview of the captured screenshot. Use crop mode to select a region.")
        self._scroll_area.setWidget(self._image_viewer)
        layout.addWidget(self._scroll_area, 1)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        # Zoom controls
        self._zoom_out_btn = QPushButton("−")
        self._zoom_out_btn.setFixedSize(32, 32)
        self._zoom_out_btn.setToolTip("Zoom Out")
        self._zoom_out_btn.setAccessibleName("Zoom out")
        self._zoom_out_btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        toolbar.addWidget(self._zoom_out_btn)

        self._zoom_in_btn = QPushButton("+")
        self._zoom_in_btn.setFixedSize(32, 32)
        self._zoom_in_btn.setToolTip("Zoom In")
        self._zoom_in_btn.setAccessibleName("Zoom in")
        self._zoom_in_btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        toolbar.addWidget(self._zoom_in_btn)

        self._fit_btn = QPushButton("Fit")
        self._fit_btn.setToolTip("Fit to Window")
        self._fit_btn.setAccessibleName("Fit to window")
        self._fit_btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        toolbar.addWidget(self._fit_btn)

        toolbar.addSpacing(20)

        # Crop toggle
        self._crop_btn = QPushButton("Crop")
        self._crop_btn.setCheckable(True)
        self._crop_btn.setToolTip("Enable crop selection")
        self._crop_btn.setAccessibleName("Toggle crop mode")
        self._crop_btn.setAccessibleDescription("When enabled, click and drag on the image to select a region to crop")
        self._crop_btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        toolbar.addWidget(self._crop_btn)

        # Reset
        self._reset_btn = QPushButton("Reset")
        self._reset_btn.setToolTip("Reset to original")
        self._reset_btn.setAccessibleName("Reset image")
        self._reset_btn.setAccessibleDescription("Revert all changes and restore the original capture")
        self._reset_btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        toolbar.addWidget(self._reset_btn)

        toolbar.addStretch()

        # Dimension info
        self._dimension_label = QLabel()
        self._dimension_label.setStyleSheet("color: #888;")
        toolbar.addWidget(self._dimension_label)

        layout.addLayout(toolbar)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self._retake_btn = QPushButton("Retake")
        self._retake_btn.setToolTip("Take a new screenshot")
        self._retake_btn.setAccessibleName("Retake capture")
        self._retake_btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        button_layout.addWidget(self._retake_btn)

        button_layout.addStretch()

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setAccessibleName("Cancel")
        self._cancel_btn.setAccessibleDescription("Close this dialog without using the capture")
        self._cancel_btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        button_layout.addWidget(self._cancel_btn)

        self._confirm_btn = QPushButton("Use This")
        self._confirm_btn.setDefault(True)
        self._confirm_btn.setAccessibleName("Use this capture")
        self._confirm_btn.setAccessibleDescription("Attach this image to your message")
        self._confirm_btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._confirm_btn.setStyleSheet(
            "QPushButton { background-color: #4285f4; color: white; padding: 8px 20px; }"
            "QPushButton:hover { background-color: #3367d6; }"
        )
        button_layout.addWidget(self._confirm_btn)

        layout.addLayout(button_layout)

    def _connect_signals(self) -> None:
        """Connect signals to slots."""
        self._zoom_in_btn.clicked.connect(self._image_viewer.zoom_in)
        self._zoom_out_btn.clicked.connect(self._image_viewer.zoom_out)
        self._fit_btn.clicked.connect(self._fit_to_window)
        self._crop_btn.toggled.connect(self._on_crop_toggled)
        self._reset_btn.clicked.connect(self._reset_image)
        self._retake_btn.clicked.connect(self._on_retake)
        self._cancel_btn.clicked.connect(self.reject)
        self._confirm_btn.clicked.connect(self.accept)
        self._image_viewer.crop_selected.connect(self._apply_crop)

    def _update_preview(self) -> None:
        """Update the preview with the current image."""
        self._image_viewer.set_image(self._current_image)
        self._update_dimension_label()

    def _update_dimension_label(self) -> None:
        """Update the dimension label."""
        self._dimension_label.setText(
            f"{self._current_image.width()} × {self._current_image.height()} px"
        )

    def _fit_to_window(self) -> None:
        """Fit image to the scroll area."""
        viewport = self._scroll_area.viewport()
        self._image_viewer.fit_to_window(
            viewport.width() - 20,
            viewport.height() - 20,
        )

    def _on_crop_toggled(self, checked: bool) -> None:
        """Handle crop mode toggle."""
        self._crop_mode = checked
        self._image_viewer.enable_crop(checked)

    def _apply_crop(self, rect: QRect) -> None:
        """Apply the crop selection.

        Args:
            rect: The crop rectangle in image coordinates.
        """
        if rect.isEmpty():
            return

        # Clamp to image bounds
        img_rect = QRect(0, 0, self._current_image.width(), self._current_image.height())
        crop_rect = rect.intersected(img_rect)

        if crop_rect.width() > 10 and crop_rect.height() > 10:
            self._current_image = self._current_image.copy(crop_rect)
            self._update_preview()

        # Exit crop mode
        self._crop_btn.setChecked(False)

    def _reset_image(self) -> None:
        """Reset to the original image."""
        self._current_image = self._original_image.copy()
        self._update_preview()
        self._image_viewer.reset_zoom()

    def _on_retake(self) -> None:
        """Request a new capture."""
        self.retake_requested.emit()
        self.reject()

    def get_image(self) -> QImage:
        """Get the final (possibly cropped) image.

        Returns:
            The current image state.
        """
        return self._current_image.copy()

    def showEvent(self, event) -> None:
        """Handle show event."""
        super().showEvent(event)
        # Fit image on first show
        self._fit_to_window()
