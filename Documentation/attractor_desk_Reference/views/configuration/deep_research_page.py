"""Deep Research settings page placeholder."""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class DeepResearchPage(QWidget):
    """Placeholder settings page for Deep Research configuration."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the Deep Research page.
        
        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("Deep Research Settings")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Placeholder message
        placeholder = QLabel("Deep Research configuration coming soon.")
        placeholder.setStyleSheet("""
            color: #6c7086;
            font-size: 16px;
            padding: 40px;
            background-color: #313244;
            border-radius: 8px;
        """)
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(placeholder)
        
        # Description
        description = QLabel(
            "Configure Deep Research settings here:\n"
            "• Research model selection\n"
            "• Search depth and iterations\n"
            "• Source preferences\n"
            "• Output format"
        )
        description.setStyleSheet("color: #6c7086; margin-top: 20px;")
        layout.addWidget(description)
        
        layout.addStretch()
