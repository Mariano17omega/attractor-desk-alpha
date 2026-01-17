"""
Main entry point for Open Canvas PySide6 application.
"""

import logging
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from ui.main_window import MainWindow
from core.config import load_config
from core.tracing import setup_langsmith_tracing

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the application."""
    # Load configuration
    try:
        load_config()
        logger.info("Configuration loaded successfully")
    except FileNotFoundError as e:
        logger.warning("Configuration file not found: %s", e)
        logger.warning("You can still run the app, but API calls will fail.")
    except ValueError as e:
        logger.error("Configuration error: %s", e)
        sys.exit(1)
    
    # Setup LangSmith tracing if available
    if setup_langsmith_tracing():
        logger.info("LangSmith tracing enabled")
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Attractor Desk")
    app.setOrganizationName("OpenCanvas")
    
    # Note: High DPI scaling is enabled by default in Qt6
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
