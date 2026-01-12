"""Capture cleanup service for removing old screenshot files."""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Set

logger = logging.getLogger(__name__)


class CaptureCleanupService:
    """Service for cleaning up old capture files."""

    def __init__(self):
        """Initialize the cleanup service."""
        pass

    def run_cleanup_if_needed(
        self,
        settings_viewmodel,
        attachment_repository,
    ) -> int:
        """Run cleanup if the last cleanup was more than 7 days ago.

        Args:
            settings_viewmodel: The settings viewmodel for capture settings.
            attachment_repository: Repository to get referenced file paths.

        Returns:
            Number of files deleted.
        """
        # Check if cleanup is needed (7+ days since last cleanup)
        last_cleanup = settings_viewmodel.capture_last_cleanup
        if last_cleanup:
            try:
                last_cleanup_dt = datetime.fromisoformat(last_cleanup)
                if datetime.now() - last_cleanup_dt < timedelta(days=7):
                    logger.debug("Cleanup not needed yet")
                    return 0
            except ValueError:
                pass  # Invalid timestamp, proceed with cleanup

        # Run cleanup
        deleted_count = self._run_cleanup(
            capture_folder=Path(settings_viewmodel.capture_storage_path),
            retention_days=settings_viewmodel.capture_retention_days,
            referenced_paths=set(attachment_repository.get_all_file_paths()),
        )

        # Update last cleanup timestamp
        settings_viewmodel.capture_last_cleanup = datetime.now().isoformat()
        settings_viewmodel.save_settings()

        return deleted_count

    def _run_cleanup(
        self,
        capture_folder: Path,
        retention_days: int,
        referenced_paths: Set[str],
    ) -> int:
        """Perform the actual cleanup.

        Args:
            capture_folder: Path to the capture storage folder.
            retention_days: Number of days to retain files.
            referenced_paths: Set of file paths that are still referenced by messages.

        Returns:
            Number of files deleted.
        """
        if not capture_folder.exists():
            return 0

        cutoff_date = datetime.now() - timedelta(days=retention_days)
        deleted_count = 0

        try:
            for file_path in capture_folder.glob("*.png"):
                # Skip if file is referenced by a message
                if str(file_path) in referenced_paths:
                    continue

                # Check file modification time
                try:
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime < cutoff_date:
                        file_path.unlink()
                        deleted_count += 1
                        logger.debug(f"Deleted old capture: {file_path}")
                except OSError as e:
                    logger.warning(f"Failed to delete {file_path}: {e}")

        except Exception as e:
            logger.error(f"Cleanup error: {e}")

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old capture files")

        return deleted_count

    def ensure_capture_folder(self, path: str) -> None:
        """Ensure the capture folder exists.

        Args:
            path: Path to the capture folder.
        """
        folder = Path(path)
        folder.mkdir(parents=True, exist_ok=True)
