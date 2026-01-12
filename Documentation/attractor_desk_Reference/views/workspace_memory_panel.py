"""Workspace memory panel widget."""

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..core.models import WorkspaceMemory, MemorySourceType
from ..viewmodels import WorkspaceMemoryViewModel


class WorkspaceMemoryPanel(QFrame):
    """Panel for viewing and managing workspace memories."""

    close_requested = Signal()

    def __init__(
        self,
        viewmodel: WorkspaceMemoryViewModel,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the memory panel.

        Args:
            viewmodel: Workspace memory viewmodel.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.viewmodel = viewmodel
        self.setObjectName("workspaceMemoryPanel")
        self.setMinimumWidth(320)
        # No maximum width - allow user to resize via splitter
        self._filter_buttons: dict[str, QPushButton] = {}
        self._setup_ui()
        self._connect_signals()
        self._refresh_list()

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header
        header = QHBoxLayout()
        title = QLabel("Workspace Memory")
        title.setObjectName("workspaceHeaderLabel")
        header.addWidget(title)
        header.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setObjectName("memoryCloseButton")
        close_btn.clicked.connect(self.close_requested.emit)
        header.addWidget(close_btn)
        layout.addLayout(header)

        # Filters - use grid layout for better space management
        filter_grid = QGridLayout()
        filter_grid.setSpacing(6)
        self._filter_group = QButtonGroup(self)
        self._filter_group.setExclusive(True)

        # Create filter buttons in a 2x2 grid
        self._add_filter_button(filter_grid, "All", None, row=0, col=0, checked=True)
        self._add_filter_button(
            filter_grid, "Chat Summaries", MemorySourceType.CHAT_SUMMARY.value, row=0, col=1
        )
        self._add_filter_button(
            filter_grid, "Agent Links", MemorySourceType.AGENT_MEMORY.value, row=1, col=0
        )
        self._add_filter_button(
            filter_grid, "User Added", MemorySourceType.USER_ADDED.value, row=1, col=1
        )

        layout.addLayout(filter_grid)

        # Search
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search memories...")
        layout.addWidget(self._search_input)

        # Memory list
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(8)
        self._list_layout.addStretch()
        self._scroll_area.setWidget(self._list_container)
        layout.addWidget(self._scroll_area, 1)

        # Add memory button
        self._add_btn = QPushButton("Add Memory")
        self._add_btn.setObjectName("newMemoryButton")
        layout.addWidget(self._add_btn)

    def _add_filter_button(
        self,
        layout: QGridLayout,
        label: str,
        source_value: Optional[str],
        row: int = 0,
        col: int = 0,
        checked: bool = False,
    ) -> None:
        """Add a filter button to the grid."""
        button = QPushButton(label)
        button.setCheckable(True)
        button.setChecked(checked)
        button.setObjectName("memoryFilterButton")
        # Allow buttons to expand to fit their content
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(button, row, col)
        self._filter_group.addButton(button)
        self._filter_buttons[label] = button
        button.clicked.connect(
            lambda checked=False, value=source_value: self._on_filter_selected(value)
        )

    def _connect_signals(self) -> None:
        """Connect signals."""
        self.viewmodel.memories_changed.connect(self._refresh_list)
        self._search_input.textChanged.connect(self.viewmodel.search)
        self._add_btn.clicked.connect(self._on_add_memory)

    def _refresh_list(self) -> None:
        """Refresh the list of memory entries."""
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.viewmodel.memories:
            empty_label = QLabel("No memories yet.")
            empty_label.setObjectName("memoryEmptyLabel")
            self._list_layout.insertWidget(0, empty_label)
            return

        for memory in self.viewmodel.memories:
            widget = self._build_memory_item(memory)
            self._list_layout.insertWidget(self._list_layout.count() - 1, widget)

    def _build_memory_item(self, memory: WorkspaceMemory) -> QWidget:
        """Build a UI widget for a memory entry."""
        frame = QFrame()
        frame.setObjectName("memoryItem")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        content = QLabel(memory.content)
        content.setWordWrap(True)
        layout.addWidget(content)

        meta_row = QHBoxLayout()
        badge = QLabel(self._source_label(memory.source_type))
        badge.setObjectName("memoryBadge")
        badge.setStyleSheet(self._source_badge_style(memory.source_type))
        meta_row.addWidget(badge)

        priority_label = QLabel(f"Priority {memory.priority}")
        priority_label.setObjectName("memoryPriority")
        meta_row.addWidget(priority_label)

        meta_row.addStretch()
        created_at = memory.created_at.strftime("%Y-%m-%d")
        date_label = QLabel(created_at)
        date_label.setObjectName("memoryDate")
        meta_row.addWidget(date_label)
        layout.addLayout(meta_row)

        actions = QHBoxLayout()
        actions.addStretch()
        edit_btn = QPushButton("Edit")
        edit_btn.setObjectName("memoryEditButton")
        delete_btn = QPushButton("Delete")
        delete_btn.setObjectName("memoryDeleteButton")
        actions.addWidget(edit_btn)
        actions.addWidget(delete_btn)
        layout.addLayout(actions)

        edit_btn.clicked.connect(
            lambda checked=False, mem=memory: self._on_edit_memory(mem)
        )
        delete_btn.clicked.connect(
            lambda checked=False, mem_id=memory.id: self.viewmodel.delete_memory(mem_id)
        )

        return frame

    def _show_memory_dialog(
        self, title: str, label: str, initial_content: str = ""
    ) -> tuple[str, bool]:
        """Show a custom memory dialog with proper sizing and word wrap.
        
        Args:
            title: Dialog title.
            label: Label text for the input.
            initial_content: Initial content for the text edit.
            
        Returns:
            Tuple of (content, accepted).
        """
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumSize(450, 300)
        dialog.resize(500, 350)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        prompt_label = QLabel(label)
        layout.addWidget(prompt_label)
        
        text_edit = QPlainTextEdit()
        text_edit.setPlainText(initial_content)
        text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(text_edit, 1)
        
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        result = dialog.exec()
        return text_edit.toPlainText(), result == QDialog.DialogCode.Accepted

    def _on_add_memory(self) -> None:
        """Handle add memory action."""
        content, ok = self._show_memory_dialog(
            "Add Memory",
            "Enter memory content:",
        )
        if not ok or not content.strip():
            return

        priority, ok = QInputDialog.getInt(
            self,
            "Priority",
            "Set priority (higher is more important):",
            value=0,
            min=-10,
            max=10,
        )
        if not ok:
            priority = 0

        self.viewmodel.add_memory(content.strip(), priority)

    def _on_edit_memory(self, memory: WorkspaceMemory) -> None:
        """Handle edit memory action."""
        content, ok = self._show_memory_dialog(
            "Edit Memory",
            "Update memory content:",
            memory.content,
        )
        if not ok:
            return

        priority, ok = QInputDialog.getInt(
            self,
            "Priority",
            "Update priority (higher is more important):",
            value=memory.priority,
            min=-10,
            max=10,
        )
        if not ok:
            priority = memory.priority

        self.viewmodel.update_memory(memory.id, content.strip(), priority)

    def _on_filter_selected(self, source_value: Optional[str]) -> None:
        """Handle filter selection."""
        self.viewmodel.filter_by_source(source_value)

    def _source_label(self, source_type: MemorySourceType) -> str:
        """Get a friendly label for source type."""
        if source_type == MemorySourceType.CHAT_SUMMARY:
            return "Chat Summary"
        if source_type == MemorySourceType.AGENT_MEMORY:
            return "Agent Memory"
        return "User Added"

    def _source_badge_style(self, source_type: MemorySourceType) -> str:
        """Get badge style based on source type."""
        if source_type == MemorySourceType.CHAT_SUMMARY:
            background = "#94e2d5"
        elif source_type == MemorySourceType.AGENT_MEMORY:
            background = "#89b4fa"
        else:
            background = "#a6e3a1"
        return (
            "QLabel {"
            f"background-color: {background};"
            "color: #1e1e2e;"
            "border-radius: 4px;"
            "padding: 2px 6px;"
            "font-size: 11px;"
            "}"
        )
