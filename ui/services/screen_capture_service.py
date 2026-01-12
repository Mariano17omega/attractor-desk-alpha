"""Screen capture utilities for the UI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from PySide6.QtCore import QRect
from PySide6.QtGui import QCursor, QGuiApplication

import mss
import mss.tools


CAPTURE_DIRECTORY = Path("/home/m/Documents/Attractor_Imagens")


@dataclass(frozen=True)
class CapturePayload:
    """In-memory capture data for preview and saving."""

    png_bytes: bytes
    width: int
    height: int


class ScreenCaptureService:
    """Capture screen images for full-screen or region selection."""

    def __init__(self, capture_dir: Optional[Path] = None):
        self._capture_dir = capture_dir or CAPTURE_DIRECTORY

    def capture_full_screen(self) -> CapturePayload:
        monitor = self._monitor_for_cursor()
        return self._grab_monitor(monitor)

    def capture_region(self, region: QRect) -> CapturePayload:
        if region.isNull() or region.width() <= 0 or region.height() <= 0:
            raise ValueError("Region capture requires a non-empty selection.")
        monitor = {
            "left": region.x(),
            "top": region.y(),
            "width": region.width(),
            "height": region.height(),
        }
        return self._grab_monitor(monitor)

    def save_capture(self, payload: CapturePayload) -> Path:
        self._capture_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"capture_{timestamp}_{uuid4().hex[:8]}.png"
        destination = self._capture_dir / filename
        destination.write_bytes(payload.png_bytes)
        return destination

    @staticmethod
    def _monitor_for_cursor() -> dict[str, int]:
        screen = QGuiApplication.screenAt(QCursor.pos())
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        if screen is None:
            raise RuntimeError("No screen available for capture.")
        geometry = screen.geometry()
        return {
            "left": geometry.x(),
            "top": geometry.y(),
            "width": geometry.width(),
            "height": geometry.height(),
        }

    @staticmethod
    def _grab_monitor(monitor: dict[str, int]) -> CapturePayload:
        with mss.mss() as capturer:
            shot = capturer.grab(monitor)
            png_bytes = mss.tools.to_png(shot.rgb, shot.size)
        return CapturePayload(
            png_bytes=png_bytes,
            width=shot.width,
            height=shot.height,
        )
