"""Shortcuts settings page with key capture editing."""

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QLineEdit,
)
from PySide6.QtGui import QKeySequence, QKeyEvent

from ...viewmodels import SettingsViewModel


class KeySequenceEdit(QLineEdit):
    """Custom line edit that captures key sequences."""
    
    key_sequence_changed = Signal(str)
    
    def __init__(self, sequence: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._sequence = sequence
        self._recording = False
        self.setText(sequence)
        self.setReadOnly(True)
        self.setPlaceholderText("Click then press keys...")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setObjectName("keySequenceEdit")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Completely transparent styling - just shows text
        self._normal_style = """
            QLineEdit {
                background: transparent;
                border: none;
                padding: 4px 8px;
                qproperty-alignment: AlignCenter;
            }
        """
        self._recording_style = """
            QLineEdit {
                background: transparent;
                border: none;
                color: #60A5FA;
                font-style: italic;
                padding: 4px 8px;
                qproperty-alignment: AlignCenter;
            }
        """
        self.setStyleSheet(self._normal_style)
    
    def mousePressEvent(self, event) -> None:
        """Start recording on click."""
        super().mousePressEvent(event)
        self._recording = True
        self.setText("Press keys...")
        self.setStyleSheet(self._recording_style)
        self.setFocus()
    
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Capture key press as shortcut."""
        if not self._recording:
            return
        
        # Escape cancels recording
        if event.key() == Qt.Key.Key_Escape:
            self._recording = False
            self.setText(self._sequence)
            self.setStyleSheet(self._normal_style)
            return
        
        # Skip modifier-only presses
        if event.key() in (
            Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta
        ):
            return
        
        # Build key sequence from modifiers + key
        modifiers = event.modifiers()
        key = event.key()
        
        # Use keyCombination for proper conversion in PySide6
        key_combo = event.keyCombination()
        sequence = QKeySequence(key_combo)
        sequence_str = sequence.toString()
        
        if sequence_str:
            self._sequence = sequence_str
            self.setText(sequence_str)
            self._recording = False
            self.setStyleSheet(self._normal_style)
            self.key_sequence_changed.emit(sequence_str)
    
    def focusOutEvent(self, event) -> None:
        """Cancel recording on focus loss."""
        super().focusOutEvent(event)
        if self._recording:
            self._recording = False
            self.setText(self._sequence)
            self.setStyleSheet(self._normal_style)


class ShortcutsPage(QWidget):
    """Settings page for keyboard shortcuts configuration."""
    
    def __init__(
        self,
        viewmodel: SettingsViewModel,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the shortcuts page.
        
        Args:
            viewmodel: The settings viewmodel.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._viewmodel = viewmodel
        self._key_editors: dict[str, KeySequenceEdit] = {}
        self._setup_ui()
        self._load_values()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("Keyboard Shortcuts")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel("Click on a key sequence, then press the new keys to change it.")
        instructions.setStyleSheet("font-style: italic; margin-bottom: 10px;")
        layout.addWidget(instructions)
        
        # Shortcuts table
        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["Action", "Key Sequence", "Description"])
        
        # Configure header
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 250)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(1, 180)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(2, 400)
        
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setDefaultSectionSize(40)
        
        layout.addWidget(self._table)
        
        # Reset button
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setMaximumWidth(150)
        reset_btn.clicked.connect(self._on_reset_clicked)
        layout.addWidget(reset_btn)
    
    def _load_values(self) -> None:
        """Load current values from viewmodel."""
        shortcuts = self._viewmodel.shortcuts
        self._table.setRowCount(len(shortcuts))
        self._key_editors.clear()
        
        for row, shortcut in enumerate(shortcuts):
            # Action (read-only)
            action_item = QTableWidgetItem(shortcut.action.replace("_", " ").title())
            action_item.setFlags(action_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            action_item.setData(Qt.ItemDataRole.UserRole, shortcut.action)
            self._table.setItem(row, 0, action_item)
            
            # Key sequence (completely transparent, looks like plain text)
            key_editor = KeySequenceEdit(shortcut.key_sequence)
            key_editor.key_sequence_changed.connect(
                lambda seq, action=shortcut.action: self._on_key_changed(action, seq)
            )
            self._table.setCellWidget(row, 1, key_editor)
            self._key_editors[shortcut.action] = key_editor
            
            # Description (read-only)
            desc_item = QTableWidgetItem(shortcut.description)
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 2, desc_item)
    
    def _on_key_changed(self, action: str, sequence: str) -> None:
        """Handle key sequence change."""
        self._viewmodel.update_shortcut(action, sequence)
    
    def _on_reset_clicked(self) -> None:
        """Reset shortcuts to defaults."""
        self._viewmodel.reset_shortcuts()
        self._load_values()
