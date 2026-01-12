"""
Main window for Open Canvas application.
"""

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QSplitter,
    QStatusBar,
    QToolBar,
    QPushButton,
    QLabel,
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QAction, QFont

from ui.widgets.chat_panel import ChatPanel
from ui.widgets.artifact_panel import ArtifactPanel
from ui.widgets.settings_dialog import SettingsDialog
from ui.viewmodels.chat_viewmodel import ChatViewModel


# Light theme stylesheet
LIGHT_THEME_STYLE = """
QMainWindow {
    background-color: #ffffff;
}

QWidget {
    font-family: 'Segoe UI', 'SF Pro Display', -apple-system, sans-serif;
    font-size: 14px;
    color: #1a1a1a;
}

QToolBar {
    background-color: #f8f9fa;
    border-bottom: 1px solid #e0e0e0;
    padding: 8px;
    spacing: 8px;
}

QToolBar QPushButton {
    background-color: transparent;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: 500;
}

QToolBar QPushButton:hover {
    background-color: #e8e8e8;
}

QToolBar QPushButton#settingsButton {
    background-color: #f0f0f0;
    border: 1px solid #d0d0d0;
}

QToolBar QPushButton#settingsButton:hover {
    background-color: #e0e0e0;
}

QStatusBar {
    background-color: #f8f9fa;
    border-top: 1px solid #e0e0e0;
    padding: 4px 8px;
    color: #666666;
}

QSplitter::handle {
    background-color: #e0e0e0;
    width: 1px;
}

QScrollArea {
    border: none;
    background-color: #ffffff;
}

QScrollBar:vertical {
    background-color: #f0f0f0;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #c0c0c0;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #a0a0a0;
}

QGroupBox {
    font-weight: bold;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #333333;
}

QLineEdit, QTextEdit, QSpinBox, QComboBox {
    border: 1px solid #d0d0d0;
    border-radius: 6px;
    padding: 8px;
    background-color: #ffffff;
}

QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #4a90d9;
    outline: none;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QPushButton {
    background-color: #4a90d9;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 6px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #3a7fc8;
}

QPushButton:pressed {
    background-color: #2a6fb8;
}

QPushButton:disabled {
    background-color: #cccccc;
    color: #888888;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #e0e0e0;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #4a90d9;
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background: #3a7fc8;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #d0d0d0;
}

QCheckBox::indicator:checked {
    background-color: #4a90d9;
    border-color: #4a90d9;
}

QTabWidget::pane {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    background-color: #ffffff;
}

QTabBar::tab {
    background-color: #f0f0f0;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-bottom: none;
}

QDialog {
    background-color: #ffffff;
}
"""


class MainWindow(QMainWindow):
    """Main application window with chat and artifact panels."""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Open Canvas")
        self.setMinimumSize(1200, 800)
        
        # Apply light theme
        self.setStyleSheet(LIGHT_THEME_STYLE)
        
        # Settings
        self._settings = {
            "model": "anthropic/claude-3.5-sonnet",
            "temperature": 0.5,
            "max_tokens": 4096,
            "streaming": True,
            "timeout": 120,
        }
        
        # Create view model
        self.view_model = ChatViewModel()
        self.view_model.set_settings(self._settings)
        
        # Setup UI
        self._setup_toolbar()
        self._setup_ui()
        self._setup_connections()
    
    def _setup_toolbar(self):
        """Setup the main toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # App title
        title_label = QLabel("Open Canvas")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #1a1a1a;
            padding: 0 16px;
        """)
        toolbar.addWidget(title_label)
        
        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().horizontalPolicy(), spacer.sizePolicy().verticalPolicy())
        spacer.setMinimumWidth(50)
        toolbar.addWidget(spacer)
        
        # Model indicator
        self.model_label = QLabel("Claude 3.5 Sonnet")
        self.model_label.setStyleSheet("""
            color: #666666;
            font-size: 13px;
            padding: 0 12px;
        """)
        toolbar.addWidget(self.model_label)
        
        # Expanding spacer
        expanding_spacer = QWidget()
        expanding_spacer.setSizePolicy(
            expanding_spacer.sizePolicy().horizontalPolicy(),
            expanding_spacer.sizePolicy().verticalPolicy()
        )
        from PySide6.QtWidgets import QSizePolicy
        expanding_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(expanding_spacer)
        
        # New chat button
        new_chat_btn = QPushButton("New Chat")
        new_chat_btn.setStyleSheet("""
            background-color: transparent;
            color: #4a90d9;
            border: 1px solid #4a90d9;
            padding: 8px 16px;
        """)
        new_chat_btn.clicked.connect(self._on_new_chat)
        toolbar.addWidget(new_chat_btn)
        
        # Settings button
        settings_btn = QPushButton("⚙ Settings")
        settings_btn.setObjectName("settingsButton")
        settings_btn.clicked.connect(self._on_settings)
        toolbar.addWidget(settings_btn)
    
    def _setup_ui(self):
        """Setup the main window UI."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        
        # Chat panel (left side)
        self.chat_panel = ChatPanel(self.view_model)
        splitter.addWidget(self.chat_panel)
        
        # Artifact panel (right side)
        self.artifact_panel = ArtifactPanel(self.view_model)
        splitter.addWidget(self.artifact_panel)
        
        # Set initial sizes (40% chat, 60% artifact)
        splitter.setSizes([480, 720])
        
        layout.addWidget(splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def _setup_connections(self):
        """Setup signal/slot connections."""
        # Connect view model signals
        self.view_model.status_changed.connect(self._on_status_changed)
        self.view_model.error_occurred.connect(self._on_error)
    
    def _on_status_changed(self, status: str):
        """Handle status changes."""
        self.status_bar.showMessage(status)
    
    def _on_error(self, error: str):
        """Handle errors."""
        self.status_bar.showMessage(f"Error: {error}")
    
    @Slot()
    def _on_new_chat(self):
        """Start a new chat."""
        self.view_model.clear_conversation()
        self.chat_panel.clear_messages()
        self.status_bar.showMessage("New chat started")
    
    @Slot()
    def _on_settings(self):
        """Open settings dialog."""
        dialog = SettingsDialog(self._settings, self)
        
        if dialog.exec() == SettingsDialog.Accepted:
            self._settings = dialog.get_settings()
            self.view_model.set_settings(self._settings)
            
            # Update model label
            model_name = self._settings.get("model", "")
            display_name = model_name.split("/")[-1] if "/" in model_name else model_name
            self.model_label.setText(display_name.replace("-", " ").title())
            
            self.status_bar.showMessage("Settings updated")
