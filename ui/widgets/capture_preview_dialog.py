"""Capture preview dialog widget."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class CapturePreviewDialog(QDialog):
    """Dialog to preview a capture and confirm, cancel, or retake."""

    RETAKE_RESULT = 2

    def __init__(self, pixmap: QPixmap, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._pixmap = pixmap
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Capture Preview")
        self.setModal(True)
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._preview_label = QLabel()
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setStyleSheet("background-color: #111827;")
        layout.addWidget(self._preview_label, 1)

        button_row = QHBoxLayout()
        button_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)

        retake_btn = QPushButton("Retake")
        retake_btn.clicked.connect(lambda: self.done(self.RETAKE_RESULT))
        button_row.addWidget(retake_btn)

        confirm_btn = QPushButton("Confirm")
        confirm_btn.clicked.connect(self.accept)
        button_row.addWidget(confirm_btn)

        layout.addLayout(button_row)
        self._update_preview()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_preview()

    def _update_preview(self) -> None:
        if self._pixmap.isNull():
            self._preview_label.setText("Preview unavailable.")
            return
        target_size = self._preview_label.size()
        if target_size.width() <= 0 or target_size.height() <= 0:
            return
        scaled = self._pixmap.scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._preview_label.setPixmap(scaled)
