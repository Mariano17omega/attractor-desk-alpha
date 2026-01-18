"""Deep Search settings page."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ui.viewmodels import SettingsViewModel


class DeepSearchPage(QWidget):
    """Settings page for Deep Search configuration."""

    def __init__(
        self,
        viewmodel: SettingsViewModel,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._viewmodel = viewmodel
        self._setup_ui()
        self._load_values()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Deep Search Settings")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        description = QLabel(
            "Configure web search capabilities. "
            "When enabled, the chat will have access to real-time web search results."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #6c7086; margin-bottom: 16px;")
        layout.addWidget(description)

        # Enable toggle
        self._enabled_check = QCheckBox("Enable Deep Search")
        self._enabled_check.setToolTip(
            "When enabled, click the 🌐 button next to the chat input to toggle"
        )
        self._enabled_check.setStyleSheet("font-weight: 500;")
        layout.addWidget(self._enabled_check)

        # Search provider selection
        provider_row = QHBoxLayout()
        provider_label = QLabel("Search Provider:")
        provider_label.setMinimumWidth(150)
        
        self._exa_radio = QRadioButton("Exa")
        self._exa_radio.setToolTip("Semantic search via exa.ai")
        self._firecrawl_radio = QRadioButton("Firecrawl")
        self._firecrawl_radio.setToolTip("Web scraping via firecrawl.dev")
        
        self._provider_group = QButtonGroup(self)
        self._provider_group.addButton(self._exa_radio, 0)
        self._provider_group.addButton(self._firecrawl_radio, 1)
        
        provider_row.addWidget(provider_label)
        provider_row.addWidget(self._exa_radio)
        provider_row.addWidget(self._firecrawl_radio)
        provider_row.addStretch()
        layout.addLayout(provider_row)

        # EXA API Key
        exa_key_row = QHBoxLayout()
        exa_key_label = QLabel("EXA API Key:")
        exa_key_label.setMinimumWidth(150)
        self._exa_key_input = QLineEdit()
        self._exa_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._exa_key_input.setPlaceholderText("Enter your EXA API key (exa.ai)")
        self._exa_key_input.setMinimumWidth(300)
        self._exa_key_input.setMaximumWidth(500)
        exa_key_row.addWidget(exa_key_label)
        exa_key_row.addWidget(self._exa_key_input)
        exa_key_row.addStretch()
        layout.addLayout(exa_key_row)

        # Firecrawl API Key
        firecrawl_key_row = QHBoxLayout()
        firecrawl_key_label = QLabel("Firecrawl API Key:")
        firecrawl_key_label.setMinimumWidth(150)
        self._firecrawl_key_input = QLineEdit()
        self._firecrawl_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._firecrawl_key_input.setPlaceholderText("Enter your Firecrawl API key (firecrawl.dev)")
        self._firecrawl_key_input.setMinimumWidth(300)
        self._firecrawl_key_input.setMaximumWidth(500)
        firecrawl_key_row.addWidget(firecrawl_key_label)
        firecrawl_key_row.addWidget(self._firecrawl_key_input)
        firecrawl_key_row.addStretch()
        layout.addLayout(firecrawl_key_row)

        # Number of results
        results_row = QHBoxLayout()
        results_label = QLabel("Search Results:")
        results_label.setMinimumWidth(150)
        self._num_results_spin = QSpinBox()
        self._num_results_spin.setRange(1, 20)
        self._num_results_spin.setValue(5)
        self._num_results_spin.setMinimumWidth(80)
        self._num_results_spin.setMaximumWidth(100)
        self._num_results_spin.setToolTip("Number of search results to retrieve (1-20)")
        results_hint = QLabel("results per query")
        results_hint.setStyleSheet("color: #6c7086;")
        results_row.addWidget(results_label)
        results_row.addWidget(self._num_results_spin)
        results_row.addWidget(results_hint)
        results_row.addStretch()
        layout.addLayout(results_row)

        # Info section
        info_container = QWidget()
        info_container.setStyleSheet(
            """
            QWidget {
                background-color: rgba(49, 50, 68, 0.4);
                border-radius: 8px;
                padding: 12px;
            }
            """
        )
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(16, 12, 16, 12)
        info_layout.setSpacing(8)

        info_title = QLabel("ℹ️  Search Providers")
        info_title.setStyleSheet("font-weight: bold; color: #cdd6f4;")
        info_layout.addWidget(info_title)

        info_text = QLabel(
            "• Exa: Semantic search for finding relevant web content (exa.ai)\n"
            "• Firecrawl: Web scraping and content extraction (firecrawl.dev)\n"
            "• Results are automatically included in the AI's context"
        )
        info_text.setStyleSheet("color: #a6adc8; line-height: 1.5;")
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)

        layout.addWidget(info_container)

        layout.addStretch()

    def _load_values(self) -> None:
        self._enabled_check.setChecked(self._viewmodel.deep_search_enabled)
        self._exa_key_input.setText(self._viewmodel.exa_api_key)
        self._firecrawl_key_input.setText(self._viewmodel.firecrawl_api_key)
        self._num_results_spin.setValue(self._viewmodel.deep_search_num_results)
        
        if self._viewmodel.search_provider == "firecrawl":
            self._firecrawl_radio.setChecked(True)
        else:
            self._exa_radio.setChecked(True)

    def _connect_signals(self) -> None:
        self._enabled_check.toggled.connect(self._on_enabled_changed)
        self._exa_key_input.textChanged.connect(self._on_exa_key_changed)
        self._firecrawl_key_input.textChanged.connect(self._on_firecrawl_key_changed)
        self._num_results_spin.valueChanged.connect(self._on_num_results_changed)
        self._provider_group.buttonClicked.connect(self._on_provider_changed)

    def _on_enabled_changed(self, checked: bool) -> None:
        self._viewmodel.deep_search_enabled = checked

    def _on_exa_key_changed(self, text: str) -> None:
        self._viewmodel.exa_api_key = text

    def _on_firecrawl_key_changed(self, text: str) -> None:
        self._viewmodel.firecrawl_api_key = text

    def _on_num_results_changed(self, value: int) -> None:
        self._viewmodel.deep_search_num_results = value

    def _on_provider_changed(self) -> None:
        if self._firecrawl_radio.isChecked():
            self._viewmodel.search_provider = "firecrawl"
        else:
            self._viewmodel.search_provider = "exa"
