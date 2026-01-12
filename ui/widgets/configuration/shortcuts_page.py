"""Shortcuts settings page."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QKeySequenceEdit,
    QVBoxLayout,
    QWidget,
)

from ui.viewmodels.settings_viewmodel import SettingsViewModel


class ShortcutsPage(QWidget):
    """Settings page for configuring keyboard shortcuts."""

    def __init__(
        self,
        viewmodel: SettingsViewModel,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._viewmodel = viewmodel
        self._inputs: dict[str, QKeySequenceEdit] = {}
        self._setup_ui()
        self._refresh_bindings()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Shortcuts Settings")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 6px;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Customize keyboard shortcuts. Changes apply after saving settings."
        )
        subtitle.setStyleSheet("color: #6c7086; margin-bottom: 8px;")
        layout.addWidget(subtitle)

        for definition in self._viewmodel.shortcut_definitions:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(12)

            label_col = QVBoxLayout()
            label_col.setSpacing(2)
            label = QLabel(definition.label)
            label.setStyleSheet("font-size: 14px; font-weight: 600;")
            desc = QLabel(definition.description)
            desc.setStyleSheet("color: #6c7086; font-size: 12px;")
            desc.setWordWrap(True)
            label_col.addWidget(label)
            label_col.addWidget(desc)

            input_field = QKeySequenceEdit()
            input_field.setFixedWidth(200)

            clear_btn = QPushButton("Clear")
            clear_btn.setFixedWidth(70)
            clear_btn.clicked.connect(
                lambda _checked=False, action_id=definition.action_id: self._clear_binding(
                    action_id
                )
            )

            self._inputs[definition.action_id] = input_field

            row_layout.addLayout(label_col, 1)
            row_layout.addWidget(input_field, 0, Qt.AlignmentFlag.AlignRight)
            row_layout.addWidget(clear_btn, 0, Qt.AlignmentFlag.AlignRight)

            layout.addWidget(row)

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setFixedWidth(180)
        reset_btn.clicked.connect(self._on_reset_clicked)
        layout.addWidget(reset_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        layout.addStretch()

    def _connect_signals(self) -> None:
        for action_id, widget in self._inputs.items():
            widget.keySequenceChanged.connect(
                lambda sequence, aid=action_id: self._on_sequence_changed(aid, sequence)
            )
        self._viewmodel.shortcuts_changed.connect(self._refresh_bindings)

    def _refresh_bindings(self) -> None:
        for action_id, widget in self._inputs.items():
            sequence = self._viewmodel.get_shortcut_sequence(action_id)
            widget.blockSignals(True)
            widget.setKeySequence(QKeySequence(sequence))
            widget.blockSignals(False)

    def _on_sequence_changed(self, action_id: str, sequence: QKeySequence) -> None:
        self._viewmodel.set_shortcut_sequence(action_id, sequence.toString())

    def _clear_binding(self, action_id: str) -> None:
        widget = self._inputs.get(action_id)
        if widget is None:
            return
        widget.blockSignals(True)
        widget.clear()
        widget.blockSignals(False)
        self._viewmodel.set_shortcut_sequence(action_id, "")

    def _on_reset_clicked(self) -> None:
        self._viewmodel.reset_shortcuts()
