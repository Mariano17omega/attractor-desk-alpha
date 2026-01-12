"""Logging configuration for the application."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}


def _parse_level(value: Optional[str], default: int) -> int:
    if not value:
        return default
    return _LEVELS.get(value.upper(), default)


def _install_excepthook() -> None:
    if getattr(_install_excepthook, "_installed", False):
        return

    def handle_exception(exc_type, exc, tb) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        logger = logging.getLogger("uncaught")
        logger.critical("Unhandled exception", exc_info=(exc_type, exc, tb))
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = handle_exception
    _install_excepthook._installed = True


def configure_logging(
    log_dir: Optional[Path] = None,
    file_level: Optional[str] = None,
    console_level: Optional[str] = None,
) -> Path:
    """Configure application logging."""
    log_dir = log_dir or (Path.home() / ".attractor_desk" / "logs")
    log_file = log_dir / "attractor_desk.log"

    file_level_value = _parse_level(
        file_level or os.getenv("ATTRACTOR_DESK_LOG_FILE_LEVEL"),
        logging.INFO,
    )
    console_level_value = _parse_level(
        console_level or os.getenv("ATTRACTOR_DESK_LOG_CONSOLE_LEVEL"),
        logging.INFO,
    )

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )

    handlers = []
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=2 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(file_level_value)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    except OSError:
        pass

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level_value)
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)

    logging.basicConfig(
        level=min(file_level_value, console_level_value),
        handlers=handlers,
        force=True,
    )
    logging.captureWarnings(True)
    _install_excepthook()

    logging.getLogger(__name__).debug("Logging initialized at %s", log_file)
    return log_file
