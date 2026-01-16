"""Filesystem watcher for global PDF indexing."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QFileSystemWatcher, QTimer, Signal

logger = logging.getLogger(__name__)


class PdfWatcherService(QObject):
    """Watch a folder for PDF changes with debounce and retries."""

    new_pdfs_detected = Signal(list)
    watcher_error = Signal(str)

    def __init__(
        self,
        parent: Optional[QObject] = None,
        debounce_ms: int = 2500,
        max_retries: int = 3,
    ):
        super().__init__(parent)
        self._debounce_ms = debounce_ms
        self._max_retries = max_retries
        self._watcher = QFileSystemWatcher(self)
        self._watcher.directoryChanged.connect(self._on_directory_changed)
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(self._debounce_ms)
        self._debounce_timer.timeout.connect(self._emit_pending)
        self._folder_path: Optional[Path] = None
        self._pending_paths: set[str] = set()
        self._known_mtimes: dict[str, float] = {}
        self._retry_counts: dict[str, int] = {}

    def start(self, folder_path: str) -> None:
        folder = Path(folder_path).expanduser()
        if not folder.exists() or not folder.is_dir():
            self.watcher_error.emit(f"Folder not found: {folder_path}")
            return
        self.stop()
        self._folder_path = folder
        self._watcher.addPath(str(folder))
        self._scan_and_queue()

    def stop(self) -> None:
        if self._folder_path is not None:
            self._watcher.removePath(str(self._folder_path))
        self._folder_path = None
        self._pending_paths.clear()
        self._known_mtimes.clear()
        self._retry_counts.clear()

    def schedule_retry(self, pdf_path: str) -> None:
        retry_count = self._retry_counts.get(pdf_path, 0) + 1
        self._retry_counts[pdf_path] = retry_count
        if retry_count > self._max_retries:
            return
        QTimer.singleShot(self._debounce_ms, lambda: self._queue_path(pdf_path))

    def _on_directory_changed(self, _path: str) -> None:
        self._scan_and_queue()

    def _scan_and_queue(self) -> None:
        if self._folder_path is None:
            return
        pdf_paths = [str(path) for path in self._folder_path.rglob("*.pdf")]
        current_mtimes: dict[str, float] = {}
        for pdf_path in pdf_paths:
            path_obj = Path(pdf_path)
            try:
                mtime = path_obj.stat().st_mtime
            except OSError as exc:
                logger.warning("Failed to stat %s: %s", pdf_path, exc)
                continue
            current_mtimes[pdf_path] = mtime
            if self._known_mtimes.get(pdf_path) != mtime:
                self._queue_path(pdf_path)
        self._known_mtimes = current_mtimes

    def _queue_path(self, pdf_path: str) -> None:
        self._pending_paths.add(pdf_path)
        if not self._debounce_timer.isActive():
            self._debounce_timer.start()

    def _emit_pending(self) -> None:
        if not self._pending_paths:
            return
        paths = sorted(self._pending_paths)
        self._pending_paths.clear()
        self.new_pdfs_detected.emit(paths)
