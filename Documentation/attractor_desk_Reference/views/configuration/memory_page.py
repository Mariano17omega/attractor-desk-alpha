"""Memory settings page."""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...viewmodels import SettingsViewModel
from ..toggle_switch import ToggleSwitch


class MemoryPage(QWidget):
    """Settings page for workspace memory and capture configuration."""

    def __init__(
        self,
        viewmodel: SettingsViewModel,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the memory settings page.

        Args:
            viewmodel: The settings viewmodel.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._viewmodel = viewmodel
        self._setup_ui()
        self._load_values()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        from PySide6.QtCore import Qt
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Memory Settings Section
        title = QLabel("Memory Settings")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        # Auto-summarize toggle row
        auto_summarize_row = QHBoxLayout()
        auto_summarize_label = QLabel("Auto-summarize chats")
        auto_summarize_label.setMinimumWidth(200)
        
        self._auto_summarize_switch = ToggleSwitch()
        self._auto_summarize_switch.setAccessibleName("Auto-summarize chats")
        self._auto_summarize_switch.setAccessibleDescription("Automatically generate summaries for chat conversations")
        self._auto_summarize_switch.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        
        auto_summarize_row.addWidget(auto_summarize_label)
        auto_summarize_row.addWidget(self._auto_summarize_switch)
        auto_summarize_row.addStretch()
        layout.addLayout(auto_summarize_row)

        token_row = QHBoxLayout()
        token_label = QLabel("Max workspace memory tokens:")
        token_label.setMinimumWidth(200)
        self._token_spin = QSpinBox()
        self._token_spin.setRange(0, 10000)
        self._token_spin.setSingleStep(250)
        self._token_spin.setAccessibleName("Maximum workspace memory tokens")
        self._token_spin.setAccessibleDescription("Maximum number of tokens to store in workspace memory")
        self._token_spin.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        token_row.addWidget(token_label)
        token_row.addWidget(self._token_spin)
        token_row.addStretch()
        layout.addLayout(token_row)

        # Separator
        separator = QLabel("")
        separator.setFixedHeight(20)
        layout.addWidget(separator)

        # Capture Settings Section
        capture_title = QLabel("Screen Capture Settings")
        capture_title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(capture_title)

        # Capture storage path
        capture_path_row = QHBoxLayout()
        capture_path_label = QLabel("Capture storage folder:")
        
        self._capture_path_edit = QLineEdit()
        self._capture_path_edit.setReadOnly(True) 
        self._capture_path_edit.setFixedWidth(400)
        self._capture_path_edit.setAccessibleName("Capture storage folder path")
        self._capture_path_edit.setAccessibleDescription("Folder where screenshots are saved")
        self._capture_browse_btn = QPushButton("Browse...")
        self._capture_browse_btn.setAccessibleName("Browse for capture folder")
        self._capture_browse_btn.setFixedWidth(100)
        self._capture_browse_btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        capture_path_row.addWidget(capture_path_label)
        capture_path_row.addWidget(self._capture_path_edit)
        capture_path_row.addWidget(self._capture_browse_btn)
        capture_path_row.addStretch()
        layout.addLayout(capture_path_row)

        # Capture retention days
        retention_row = QHBoxLayout()
        retention_label = QLabel("Delete captures after (days):")
        retention_label.setMinimumWidth(200)
        self._retention_spin = QSpinBox()
        self._retention_spin.setRange(1, 365)
        self._retention_spin.setSingleStep(7)
        self._retention_spin.setAccessibleName("Capture retention days")
        self._retention_spin.setAccessibleDescription("Number of days to keep captures before automatic deletion")
        self._retention_spin.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        retention_row.addWidget(retention_label)
        retention_row.addWidget(self._retention_spin)
        retention_row.addStretch()
        layout.addLayout(retention_row)

        layout.addStretch()

    def _load_values(self) -> None:
        """Load current values from viewmodel."""
        self._auto_summarize_switch.setChecked(self._viewmodel.auto_summarize)
        self._token_spin.setValue(self._viewmodel.max_workspace_memory_tokens)
        self._capture_path_edit.setText(self._viewmodel.capture_storage_path)
        self._retention_spin.setValue(self._viewmodel.capture_retention_days)

    def _connect_signals(self) -> None:
        """Connect signals to update viewmodel."""
        self._auto_summarize_switch.toggled.connect(self._on_auto_summarize_changed)
        self._token_spin.valueChanged.connect(self._on_token_limit_changed)
        self._capture_browse_btn.clicked.connect(self._on_browse_capture_path)
        self._retention_spin.valueChanged.connect(self._on_retention_changed)

    def _on_auto_summarize_changed(self, checked: bool) -> None:
        """Handle auto-summarize toggle."""
        self._viewmodel.auto_summarize = checked

    def _on_token_limit_changed(self, value: int) -> None:
        """Handle token limit change."""
        self._viewmodel.max_workspace_memory_tokens = value

    def _on_browse_capture_path(self) -> None:
        """Handle capture path browse button."""
        current_path = self._viewmodel.capture_storage_path
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Capture Storage Folder",
            current_path,
            QFileDialog.Option.ShowDirsOnly,
        )
        if folder:
            self._capture_path_edit.setText(folder)
            self._viewmodel.capture_storage_path = folder

    def _on_retention_changed(self, value: int) -> None:
        """Handle retention days change."""
        self._viewmodel.capture_retention_days = value
