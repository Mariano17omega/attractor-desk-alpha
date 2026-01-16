"""Tests for PDF watcher service."""

from core.services.pdf_watcher_service import PdfWatcherService


def test_pdf_watcher_emits_new_paths(tmp_path) -> None:
    watcher = PdfWatcherService(debounce_ms=0)
    captured: list[list[str]] = []
    watcher.new_pdfs_detected.connect(lambda paths: captured.append(paths))

    watcher.start(str(tmp_path))
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    watcher._scan_and_queue()
    watcher._emit_pending()

    assert captured
    assert str(pdf_path) in captured[0]
