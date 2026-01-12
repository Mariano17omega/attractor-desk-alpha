"""Placeholder settings page."""

from __future__ import annotations

from typing import Iterable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PlaceholderPage(QWidget):
    """Simple placeholder page for future settings."""

    def __init__(
        self,
        title: str,
        description: str,
        bullets: Optional[Iterable[str]] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._title = title
        self._description = description
        self._bullets = list(bullets or [])
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel(self._title)
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(title)

        placeholder = QLabel(self._description)
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setWordWrap(True)
        placeholder.setStyleSheet(
            """
            color: #6c7086;
            font-size: 16px;
            padding: 32px;
            background-color: rgba(49, 50, 68, 0.4);
            border-radius: 8px;
            """
        )
        layout.addWidget(placeholder)

        if self._bullets:
            description = QLabel("\n".join(f"• {item}" for item in self._bullets))
            description.setStyleSheet("color: #6c7086; margin-top: 10px;")
            description.setWordWrap(True)
            layout.addWidget(description)

        layout.addStretch()
