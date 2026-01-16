"""PDF viewer widget for ChatPDF artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class PdfViewerWidget(QWidget):
    """Simple PDF viewer with navigation controls."""

    page_changed = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._document = QPdfDocument(self)
        self._view = QPdfView(self)
        self._view.setDocument(self._document)
        self._view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self._current_page = 0
        self._total_pages = 0
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QHBoxLayout()
        self._status_label = QLabel("Ready")
        self._status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._status_label.setStyleSheet("color: #6c7086;")

        self._prev_button = QToolButton()
        self._prev_button.setText("◀")
        self._next_button = QToolButton()
        self._next_button.setText("▶")
        self._page_input = QLineEdit()
        self._page_input.setFixedWidth(60)
        self._page_input.setAlignment(Qt.AlignCenter)
        self._page_label = QLabel("/ 0")

        self._zoom_out = QToolButton()
        self._zoom_out.setText("−")
        self._zoom_in = QToolButton()
        self._zoom_in.setText("+")

        toolbar.addWidget(self._status_label)
        toolbar.addStretch()
        toolbar.addWidget(self._prev_button)
        toolbar.addWidget(self._page_input)
        toolbar.addWidget(self._page_label)
        toolbar.addWidget(self._next_button)
        toolbar.addSpacing(12)
        toolbar.addWidget(self._zoom_out)
        toolbar.addWidget(self._zoom_in)

        layout.addLayout(toolbar)
        layout.addWidget(self._view, stretch=1)

        self._prev_button.clicked.connect(self._on_prev)
        self._next_button.clicked.connect(self._on_next)
        self._page_input.returnPressed.connect(self._on_page_input)
        self._zoom_out.clicked.connect(lambda: self._adjust_zoom(-0.1))
        self._zoom_in.clicked.connect(lambda: self._adjust_zoom(0.1))

    def load_pdf(self, pdf_path: str) -> bool:
        if not Path(pdf_path).exists():
            self.set_status("PDF not found")
            return False
        status = self._document.load(pdf_path)
        if status != QPdfDocument.Status.Ready:
            self.set_status("Failed to load PDF")
            return False
        self._total_pages = self._document.pageCount()
        self._current_page = 0
        self._view.setPage(self._current_page)
        self._page_label.setText(f"/ {self._total_pages}")
        self._page_input.setText(str(self._current_page + 1))
        return True

    def set_status(self, status: str) -> None:
        self._status_label.setText(status)

    def set_page(self, page_index: int) -> None:
        if self._total_pages <= 0:
            return
        page_index = max(0, min(self._total_pages - 1, page_index))
        if page_index != self._current_page:
            self._current_page = page_index
            self._view.setPage(self._current_page)
            self._page_input.setText(str(self._current_page + 1))
            self.page_changed.emit(self._current_page)

    def _on_prev(self) -> None:
        self.set_page(self._current_page - 1)

    def _on_next(self) -> None:
        self.set_page(self._current_page + 1)

    def _on_page_input(self) -> None:
        text = self._page_input.text().strip()
        try:
            page = int(text) - 1
        except ValueError:
            return
        self.set_page(page)

    def _adjust_zoom(self, delta: float) -> None:
        zoom = self._view.zoomFactor() + delta
        zoom = max(0.2, min(3.0, zoom))
        self._view.setZoomFactor(zoom)
