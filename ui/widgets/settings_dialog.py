"""
Settings dialog for Open Canvas.
Allows users to configure LLM model, temperature, and other options.
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QSlider,
    QSpinBox,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QDialogButtonBox,
    QDoubleSpinBox,
    QCheckBox,
)
from PySide6.QtCore import Qt, Signal


# Available models through OpenRouter
AVAILABLE_MODELS = [
    ("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet"),
    ("anthropic/claude-3-opus", "Claude 3 Opus"),
    ("anthropic/claude-3-haiku", "Claude 3 Haiku"),
    ("openai/gpt-4o", "GPT-4o"),
    ("openai/gpt-4o-mini", "GPT-4o Mini"),
    ("openai/gpt-4-turbo", "GPT-4 Turbo"),
    ("google/gemini-pro-1.5", "Gemini Pro 1.5"),
    ("google/gemini-flash-1.5", "Gemini Flash 1.5"),
    ("meta-llama/llama-3.1-70b-instruct", "Llama 3.1 70B"),
    ("meta-llama/llama-3.1-8b-instruct", "Llama 3.1 8B"),
    ("mistralai/mixtral-8x7b-instruct", "Mixtral 8x7B"),
    ("deepseek/deepseek-chat", "DeepSeek Chat"),
]


class SettingsDialog(QDialog):
    """Settings dialog for configuring LLM parameters."""
    
    settings_changed = Signal(dict)
    
    def __init__(self, current_settings: dict = None, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Settings")
        self.setMinimumWidth(450)
        
        self._current_settings = current_settings or {}
        
        self._setup_ui()
        self._load_current_settings()
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # --- Model Settings Group ---
        model_group = QGroupBox("Model Settings")
        model_layout = QFormLayout(model_group)
        model_layout.setSpacing(12)
        
        # Model selection
        self.model_combo = QComboBox()
        for model_id, model_name in AVAILABLE_MODELS:
            self.model_combo.addItem(model_name, model_id)
        model_layout.addRow("Model:", self.model_combo)
        
        # Custom model input
        self.custom_model_edit = QLineEdit()
        self.custom_model_edit.setPlaceholderText("e.g., anthropic/claude-3.5-sonnet")
        model_layout.addRow("Custom Model:", self.custom_model_edit)
        
        # Temperature
        temp_layout = QHBoxLayout()
        self.temperature_slider = QSlider(Qt.Horizontal)
        self.temperature_slider.setMinimum(0)
        self.temperature_slider.setMaximum(100)
        self.temperature_slider.setValue(50)
        self.temperature_slider.setTickPosition(QSlider.TicksBelow)
        self.temperature_slider.setTickInterval(10)
        
        self.temperature_label = QLabel("0.50")
        self.temperature_label.setMinimumWidth(40)
        self.temperature_slider.valueChanged.connect(self._on_temperature_changed)
        
        temp_layout.addWidget(self.temperature_slider)
        temp_layout.addWidget(self.temperature_label)
        model_layout.addRow("Temperature:", temp_layout)
        
        # Max tokens
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setMinimum(100)
        self.max_tokens_spin.setMaximum(128000)
        self.max_tokens_spin.setValue(4096)
        self.max_tokens_spin.setSingleStep(256)
        model_layout.addRow("Max Tokens:", self.max_tokens_spin)
        
        layout.addWidget(model_group)
        
        # --- API Settings Group ---
        api_group = QGroupBox("API Configuration")
        api_layout = QFormLayout(api_group)
        api_layout.setSpacing(12)
        
        # API Key (masked)
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("OpenRouter API Key")
        api_layout.addRow("API Key:", self.api_key_edit)
        
        # Show API key checkbox
        self.show_key_check = QCheckBox("Show API Key")
        self.show_key_check.toggled.connect(self._toggle_api_key_visibility)
        api_layout.addRow("", self.show_key_check)
        
        layout.addWidget(api_group)
        
        # --- Advanced Settings Group ---
        advanced_group = QGroupBox("Advanced")
        advanced_layout = QFormLayout(advanced_group)
        advanced_layout.setSpacing(12)
        
        # Streaming
        self.streaming_check = QCheckBox("Enable streaming")
        self.streaming_check.setChecked(True)
        advanced_layout.addRow("", self.streaming_check)
        
        # Timeout
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setMinimum(10)
        self.timeout_spin.setMaximum(300)
        self.timeout_spin.setValue(120)
        self.timeout_spin.setSuffix(" seconds")
        advanced_layout.addRow("Timeout:", self.timeout_spin)
        
        layout.addWidget(advanced_group)
        
        # --- Buttons ---
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.RestoreDefaults
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self._restore_defaults)
        
        layout.addWidget(button_box)
    
    def _on_temperature_changed(self, value: int):
        """Update temperature label when slider changes."""
        temp = value / 100.0
        self.temperature_label.setText(f"{temp:.2f}")
    
    def _toggle_api_key_visibility(self, show: bool):
        """Toggle API key visibility."""
        self.api_key_edit.setEchoMode(
            QLineEdit.Normal if show else QLineEdit.Password
        )
    
    def _load_current_settings(self):
        """Load current settings into the UI."""
        # Model
        model = self._current_settings.get("model", "anthropic/claude-3.5-sonnet")
        index = self.model_combo.findData(model)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        else:
            self.custom_model_edit.setText(model)
        
        # Temperature
        temp = self._current_settings.get("temperature", 0.5)
        self.temperature_slider.setValue(int(temp * 100))
        
        # Max tokens
        max_tokens = self._current_settings.get("max_tokens", 4096)
        self.max_tokens_spin.setValue(max_tokens)
        
        # API Key (should be provided in current_settings from ViewModel)
        api_key = self._current_settings.get("api_key", "")
        self.api_key_edit.setText(api_key)
        
        # Streaming
        streaming = self._current_settings.get("streaming", True)
        self.streaming_check.setChecked(streaming)
        
        # Timeout
        timeout = self._current_settings.get("timeout", 120)
        self.timeout_spin.setValue(timeout)
    
    def _restore_defaults(self):
        """Restore default settings."""
        self.model_combo.setCurrentIndex(0)
        self.custom_model_edit.clear()
        self.temperature_slider.setValue(50)
        self.max_tokens_spin.setValue(4096)
        self.streaming_check.setChecked(True)
        self.timeout_spin.setValue(120)
    
    def get_settings(self) -> dict:
        """Get the current settings from the dialog."""
        # Use custom model if specified, otherwise selected model
        model = self.custom_model_edit.text().strip()
        if not model:
            model = self.model_combo.currentData()
        
        return {
            "model": model,
            "temperature": self.temperature_slider.value() / 100.0,
            "max_tokens": self.max_tokens_spin.value(),
            "api_key": self.api_key_edit.text().strip() or None,
            "streaming": self.streaming_check.isChecked(),
            "timeout": self.timeout_spin.value(),
        }
    
    def accept(self):
        """Handle dialog acceptance."""
        settings = self.get_settings()
        self.settings_changed.emit(settings)
        super().accept()
