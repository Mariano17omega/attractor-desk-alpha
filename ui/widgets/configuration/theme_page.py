"""Theme settings page."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFontComboBox,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from core.models import ThemeMode
from ui.viewmodels import SettingsViewModel


class ThemePage(QWidget):
    """Settings page for theme configuration."""

    transparency_preview_requested = Signal(int)

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

        title = QLabel("Theme Settings")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        mode_row = QHBoxLayout()
        mode_label = QLabel("Theme Mode:")
        mode_label.setMinimumWidth(150)
        self._mode_combo = QComboBox()
        self._mode_combo.addItem("Dark", ThemeMode.DARK)
        self._mode_combo.addItem("Light", ThemeMode.LIGHT)
        self._mode_combo.setMinimumWidth(200)
        self._mode_combo.setMaximumWidth(400)
        mode_row.addWidget(mode_label)
        mode_row.addWidget(self._mode_combo)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        font_row = QHBoxLayout()
        font_label = QLabel("Font Family:")
        font_label.setMinimumWidth(150)
        self._font_combo = QFontComboBox()
        self._font_combo.setMinimumWidth(200)
        self._font_combo.setMaximumWidth(400)
        font_row.addWidget(font_label)
        font_row.addWidget(self._font_combo)
        font_row.addStretch()
        layout.addLayout(font_row)

        trans_row = QHBoxLayout()
        trans_label = QLabel("Window Transparency:")
        trans_label.setMinimumWidth(150)
        self._transparency_slider = QSlider(Qt.Orientation.Horizontal)
        self._transparency_slider.setRange(30, 100)
        self._transparency_slider.setValue(100)
        self._transparency_slider.setMinimumWidth(200)
        self._transparency_slider.setMaximumWidth(400)
        self._transparency_value = QLabel("100%")
        self._transparency_value.setMinimumWidth(50)
        trans_row.addWidget(trans_label)
        trans_row.addWidget(self._transparency_slider)
        trans_row.addWidget(self._transparency_value)
        trans_row.addStretch()
        layout.addLayout(trans_row)

        self._keep_above_check = QCheckBox("Keep window above others")
        layout.addWidget(self._keep_above_check)

        layout.addStretch()

    def _load_values(self) -> None:
        index = self._mode_combo.findData(self._viewmodel.theme_mode)
        if index >= 0:
            self._mode_combo.setCurrentIndex(index)

        self._font_combo.setCurrentFont(self._font_combo.font())
        for i in range(self._font_combo.count()):
            if self._font_combo.itemText(i) == self._viewmodel.font_family:
                self._font_combo.setCurrentIndex(i)
                break

        self._transparency_slider.setValue(self._viewmodel.transparency)
        self._transparency_value.setText(f"{self._viewmodel.transparency}%")
        self._keep_above_check.setChecked(self._viewmodel.keep_above)

    def _connect_signals(self) -> None:
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self._font_combo.currentFontChanged.connect(self._on_font_changed)
        self._transparency_slider.valueChanged.connect(self._on_transparency_changed)
        self._keep_above_check.toggled.connect(self._on_keep_above_changed)

    def _on_mode_changed(self, index: int) -> None:
        mode = self._mode_combo.itemData(index)
        if mode:
            self._viewmodel.theme_mode = mode

    def _on_font_changed(self) -> None:
        self._viewmodel.font_family = self._font_combo.currentFont().family()

    def _on_transparency_changed(self, value: int) -> None:
        self._transparency_value.setText(f"{value}%")
        self._viewmodel.transparency = value
        self.transparency_preview_requested.emit(value)

    def _on_keep_above_changed(self, checked: bool) -> None:
        self._viewmodel.keep_above = checked
