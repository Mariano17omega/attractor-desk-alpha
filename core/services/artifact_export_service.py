"""Artifact export service.

Exports artifacts to disk as Markdown files, supporting both text and code artifacts.
Handles naming conventions for PDF ingestions vs chat-created artifacts.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from core.types import (
    ArtifactCollectionV1,
    ArtifactEntry,
    ArtifactMarkdownV3,
    ArtifactCodeV3,
)
from core.persistence.artifact_repository import ArtifactRepository

logger = logging.getLogger(__name__)

# Default export directory
EXPORT_DIR = Path.home() / "Documents" / "Artifacts" / "Articles"


class ArtifactExportService:
    """Service for exporting artifacts to disk.

    Export behavior:
    - Text artifacts: exported as .md files
    - Code artifacts: exported as fenced Markdown with language specified
    - PDF ingestions: use PDF base filename, append -2, -3 etc. for duplicates
    - Chat artifacts: use {session_title}-{tab_label}.md, overwrite on update
    """

    def __init__(self, artifact_repository: ArtifactRepository):
        self._artifact_repo = artifact_repository
        self._export_dir = EXPORT_DIR

    def set_export_dir(self, path: Path) -> None:
        """Override the export directory."""
        self._export_dir = path

    def export_session(
        self,
        session_id: str,
        session_title: str,
    ) -> list[Path]:
        """Export all artifacts for a session to disk.

        Args:
            session_id: ID of the session to export.
            session_title: Title of the session (for naming chat artifacts).

        Returns:
            List of paths to exported files.
        """
        collection = self._artifact_repo.get_collection(session_id)
        if collection is None or not collection.artifacts:
            return []

        # Ensure export directory exists
        self._export_dir.mkdir(parents=True, exist_ok=True)

        exported: list[Path] = []
        text_count = 0
        code_count = 0

        for entry in collection.artifacts:
            artifact = entry.artifact
            if not artifact.contents:
                continue

            # Get current content
            current_content = artifact.contents[-1]

            # Determine if code or text
            is_code = current_content.type == "code"
            if is_code:
                code_count += 1
                tab_label = f"Code_{code_count}"
            else:
                text_count += 1
                tab_label = f"Art_{text_count}"

            # Determine filename
            filename = self._get_export_filename(
                entry=entry,
                session_title=session_title,
                tab_label=tab_label,
            )

            # Format content as Markdown
            content_md = self._format_content(current_content)

            # Write file
            export_path = self._export_dir / filename
            try:
                export_path.write_text(content_md, encoding="utf-8")
                logger.info("Exported artifact to: %s", export_path)
                exported.append(export_path)

                # Update export metadata with the filename used
                if entry.export_meta.export_filename != filename:
                    entry.export_meta.export_filename = filename
                    self._artifact_repo.save_collection(session_id, collection)

            except OSError as e:
                logger.error("Failed to export artifact: %s", e)

        return exported

    def _get_export_filename(
        self,
        entry: ArtifactEntry,
        session_title: str,
        tab_label: str,
    ) -> str:
        """Determine the export filename for an artifact.

        Rules:
        - If already exported, reuse stable filename
        - For PDF ingestions: use source PDF name, append suffix if exists
        - For chat artifacts: use {session_title}-{tab_label}.md
        """
        # Reuse stable filename if available
        if entry.export_meta.export_filename:
            return entry.export_meta.export_filename

        # PDF ingestion
        if entry.export_meta.source_pdf:
            base = self._sanitize_filename(entry.export_meta.source_pdf)
            return self._get_unique_filename(base)

        # Chat-created artifact
        safe_title = self._sanitize_filename(session_title)
        return f"{safe_title}-{tab_label}.md"

    def _get_unique_filename(self, base: str) -> str:
        """Get a unique filename, appending -2, -3 etc. if file exists."""
        candidate = f"{base}.md"
        if not (self._export_dir / candidate).exists():
            return candidate

        counter = 2
        while True:
            candidate = f"{base}-{counter}.md"
            if not (self._export_dir / candidate).exists():
                return candidate
            counter += 1

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a string for use as a filename."""
        # Remove/replace problematic characters
        safe = name.replace("/", "-").replace("\\", "-")
        safe = "".join(c for c in safe if c.isalnum() or c in (" ", "-", "_", "."))
        return safe.strip()[:50] or "untitled"

    def _format_content(self, content) -> str:
        """Format artifact content as Markdown."""
        if isinstance(content, ArtifactMarkdownV3) or content.type == "text":
            return content.full_markdown

        # Code artifact: wrap in fenced code block
        if isinstance(content, ArtifactCodeV3) or content.type == "code":
            lang = (
                content.language.value
                if hasattr(content.language, "value")
                else str(content.language)
            )
            return f"```{lang}\n{content.code}\n```\n"

        return ""
