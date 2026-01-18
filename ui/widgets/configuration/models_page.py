"""Models settings page."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.viewmodels import SettingsViewModel
from ui.viewmodels.settings import DEFAULT_IMAGE_MODELS


class ModelsPage(QWidget):
    """Settings page for model configuration."""

    def __init__(
        self,
        viewmodel: SettingsViewModel,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._viewmodel = viewmodel
        self._api_key_visible = False
        self._setup_ui()
        self._load_values()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Models Settings")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        api_section = QLabel("OpenRouter API Key")
        api_section.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(api_section)

        api_row = QHBoxLayout()
        self._api_key_input = QLineEdit()
        self._api_key_input.setPlaceholderText("Enter your OpenRouter API key")
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_input.setFixedWidth(400)

        self._toggle_visibility_btn = QPushButton("Show")
        self._toggle_visibility_btn.setFixedWidth(80)

        api_row.addWidget(self._api_key_input)
        api_row.addWidget(self._toggle_visibility_btn)
        api_row.addStretch()
        layout.addLayout(api_row)

        model_section = QLabel("Default Model")
        model_section.setStyleSheet(
            "font-size: 14px; font-weight: bold; margin-top: 10px;"
        )
        layout.addWidget(model_section)

        model_row = QHBoxLayout()
        model_row.setContentsMargins(0, 0, 0, 0)
        self._default_model_combo = QComboBox()
        self._default_model_combo.setFixedWidth(400)
        self._default_model_combo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        model_row.addWidget(self._default_model_combo)

        model_row_widget = QWidget()
        model_row_widget.setLayout(model_row)
        model_row_widget.setFixedWidth(400)
        model_row_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout.addWidget(model_row_widget, alignment=Qt.AlignLeft)
        layout.setAlignment(model_row_widget, Qt.AlignLeft)

        image_model_section = QLabel("Default Model Image")
        image_model_section.setStyleSheet(
            "font-size: 14px; font-weight: bold; margin-top: 10px;"
        )
        layout.addWidget(image_model_section)

        image_model_row = QHBoxLayout()
        image_model_row.setContentsMargins(0, 0, 0, 0)
        self._image_model_combo = QComboBox()
        self._image_model_combo.setFixedWidth(400)
        self._image_model_combo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._image_model_combo.setFixedWidth(400)
        self._image_model_combo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._refresh_image_model_combo()
        image_model_row.addWidget(self._image_model_combo)

        image_model_row_widget = QWidget()
        image_model_row_widget.setLayout(image_model_row)
        image_model_row_widget.setFixedWidth(400)
        image_model_row_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout.addWidget(image_model_row_widget, alignment=Qt.AlignLeft)
        layout.setAlignment(image_model_row_widget, Qt.AlignLeft)

        add_model_section = QLabel("Add New Model")
        add_model_section.setStyleSheet(
            "font-size: 14px; font-weight: bold; margin-top: 10px;"
        )
        layout.addWidget(add_model_section)

        add_model_row = QHBoxLayout()
        self._add_model_input = QLineEdit()
        self._add_model_input.setPlaceholderText("Enter model ID (e.g. openai/gpt-4)")
        self._add_model_input.setFixedWidth(400)

        self._add_model_btn = QPushButton("Add")
        self._add_model_btn.setFixedWidth(80)

        add_model_row.addWidget(self._add_model_input)
        add_model_row.addWidget(self._add_model_btn)
        add_model_row.addStretch()
        add_model_row.addStretch()
        layout.addLayout(add_model_row)

        add_image_model_section = QLabel("Add New Image Model")
        add_image_model_section.setStyleSheet(
            "font-size: 14px; font-weight: bold; margin-top: 10px;"
        )
        layout.addWidget(add_image_model_section)

        add_image_model_row = QHBoxLayout()
        self._add_image_model_input = QLineEdit()
        self._add_image_model_input.setPlaceholderText("Enter image model ID (e.g. openai/gpt-4o)")
        self._add_image_model_input.setFixedWidth(400)

        self._add_image_model_btn = QPushButton("Add")
        self._add_image_model_btn.setFixedWidth(80)

        add_image_model_row.addWidget(self._add_image_model_input)
        add_image_model_row.addWidget(self._add_image_model_btn)
        add_image_model_row.addStretch()
        layout.addLayout(add_image_model_row)

        layout.addStretch()

    def _load_values(self) -> None:
        if self._viewmodel.api_key:
            self._api_key_input.setText(self._viewmodel.api_key)
        self._refresh_default_combo()
        self._refresh_image_model_combo()
        
        # Index setting is handled inside _refresh_image_model_combo now to avoid duplication logic calling it here alone


    def _refresh_default_combo(self) -> None:
        self._default_model_combo.clear()
        for model in self._viewmodel.models_list:
            self._default_model_combo.addItem(model)

        index = self._default_model_combo.findText(self._viewmodel.default_model)
        if index >= 0:
            self._default_model_combo.setCurrentIndex(index)

    def _refresh_image_model_combo(self) -> None:
        self._image_model_combo.clear()
        for model in self._viewmodel.image_models_list:
            self._image_model_combo.addItem(model)

        index = self._image_model_combo.findText(self._viewmodel.image_model)
        if index >= 0:
            self._image_model_combo.setCurrentIndex(index)

    def _connect_signals(self) -> None:
        self._api_key_input.textChanged.connect(self._on_api_key_changed)
        self._toggle_visibility_btn.clicked.connect(self._toggle_api_visibility)
        self._default_model_combo.currentTextChanged.connect(self._on_default_model_changed)
        self._image_model_combo.currentTextChanged.connect(self._on_image_model_changed)
        self._add_model_btn.clicked.connect(self._on_add_model)
        self._add_image_model_btn.clicked.connect(self._on_add_image_model)

    def _on_api_key_changed(self, text: str) -> None:
        self._viewmodel.api_key = text

    def _toggle_api_visibility(self) -> None:
        self._api_key_visible = not self._api_key_visible
        if self._api_key_visible:
            self._api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._toggle_visibility_btn.setText("Hide")
        else:
            self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._toggle_visibility_btn.setText("Show")

    def _on_default_model_changed(self, text: str) -> None:
        if text:
            self._viewmodel.default_model = text

    def _on_image_model_changed(self, text: str) -> None:
        if text:
            self._viewmodel.image_model = text

    def _on_add_model(self) -> None:
        model = self._add_model_input.text().strip()
        if model:
            self._viewmodel.add_model(model)
            self._add_model_input.clear()
            self._refresh_default_combo()

    def _on_add_image_model(self) -> None:
        model = self._add_image_model_input.text().strip()
        if model:
            self._viewmodel.add_image_model(model)
            self._add_image_model_input.clear()
            self._refresh_image_model_combo()
