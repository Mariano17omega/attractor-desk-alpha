"""Docling-based PDF to Markdown conversion service.

This service provides background-threaded PDF conversion using the Docling library,
returning Markdown output suitable for creating text artifacts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

logger = logging.getLogger(__name__)


@dataclass
class PdfConversionResult:
    """Result of a PDF to Markdown conversion."""
    success: bool
    markdown: str = ""
    source_filename: str = ""
    error_message: str = ""


def convert_pdf_to_markdown(pdf_path: str) -> PdfConversionResult:
    """Convert a PDF file to Markdown synchronously."""
    source_filename = Path(pdf_path).stem
    try:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True

        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

        result = converter.convert(pdf_path)
        markdown = result.document.export_to_markdown()
        return PdfConversionResult(
            success=True,
            markdown=markdown,
            source_filename=source_filename,
        )
    except ImportError as e:
        logger.error("Docling not installed: %s", e)
        return PdfConversionResult(
            success=False,
            source_filename=source_filename,
            error_message="Docling is not installed. Install with: pip install docling",
        )
    except Exception as e:
        logger.exception("PDF conversion failed: %s", e)
        return PdfConversionResult(
            success=False,
            source_filename=source_filename,
            error_message=f"PDF conversion failed: {e}",
        )


class _ConversionWorker(QObject):
    """Worker that runs Docling conversion in a background thread."""

    finished = Signal(PdfConversionResult)

    def __init__(self, pdf_path: str):
        super().__init__()
        self._pdf_path = pdf_path

    def run(self) -> None:
        """Perform the PDF conversion using Docling."""
        try:
            self.finished.emit(convert_pdf_to_markdown(self._pdf_path))
        finally:
            # Explicitly close thread-local database connections
            # This prevents connection leaks when worker threads terminate
            # Note: Docling may not use database, but this ensures cleanup if it does
            try:
                from core.persistence import Database
                db = Database()
                db.close()
            except Exception:
                pass  # Non-fatal if Database not used


class DoclingService(QObject):
    """Service for converting PDFs to Markdown using Docling.

    This service runs conversions in a background thread to avoid blocking the UI.

    Signals:
        conversion_complete: Emitted when a conversion finishes (success or failure).

    Example:
        service = DoclingService()
        service.conversion_complete.connect(handle_result)
        service.convert_pdf("/path/to/file.pdf")
    """

    conversion_complete = Signal(PdfConversionResult)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._thread: Optional[QThread] = None
        self._worker: Optional[_ConversionWorker] = None

    def convert_pdf(self, pdf_path: str) -> None:
        """Start converting a PDF file to Markdown in the background.

        The result will be emitted via the conversion_complete signal.

        Args:
            pdf_path: Absolute path to the PDF file to convert.
        """
        if not Path(pdf_path).exists():
            self.conversion_complete.emit(PdfConversionResult(
                success=False,
                source_filename=Path(pdf_path).stem,
                error_message=f"File not found: {pdf_path}",
            ))
            return

        # Clean up any previous conversion
        self._cleanup()

        # Set up worker and thread
        self._thread = QThread()
        self._worker = _ConversionWorker(pdf_path)
        self._worker.moveToThread(self._thread)

        # Connect signals
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup)

        # Start conversion
        self._thread.start()
        logger.info("Started PDF conversion: %s", pdf_path)

    def _on_worker_finished(self, result: PdfConversionResult) -> None:
        """Handle worker completion and emit result."""
        self.conversion_complete.emit(result)

    def _cleanup(self) -> None:
        """Clean up thread and worker resources."""
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
        if self._thread is not None:
            self._thread.deleteLater()
            self._thread = None

    def is_busy(self) -> bool:
        """Check if a conversion is currently in progress."""
        return self._thread is not None and self._thread.isRunning()
