"""Sidebar widget for workspace and chat navigation."""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..viewmodels import WorkspaceViewModel, WorkspaceMemoryViewModel


class ChatListItemWidget(QFrame):
    """Widget for a chat list item with a delete button."""
    
    clicked = Signal()
    delete_requested = Signal(str, str)
    
    def __init__(
        self,
        chat_id: str,
        title: str,
        display_title: str,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the chat list item widget.
        
        Args:
            chat_id: Chat identifier.
            title: Full chat title.
            display_title: Truncated title for display.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._chat_id = chat_id
        self._title = title
        self.setObjectName("chatListItem")
        self.setProperty("selected", False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 0, 8)
        layout.setSpacing(8)
        
        self._title_label = QLabel(display_title)
        self._title_label.setObjectName("chatListItemTitle")
        self._title_label.setToolTip(title)
        self._title_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        layout.addWidget(self._title_label)
        
        self._delete_btn = QPushButton("-")
        self._delete_btn.setObjectName("iconButton")
        self._delete_btn.setToolTip("Delete chat")
        self._delete_btn.setFixedSize(32, 32)

        action_btn_style = "font-size: 18px; font-weight: 700; padding: 0px;"
        self._delete_btn.setStyleSheet(action_btn_style)


        self._delete_btn.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self._delete_btn.clicked.connect(self._on_delete_clicked)
        layout.addWidget(self._delete_btn)
    
    def set_selected(self, selected: bool) -> None:
        """Update selection state for styling."""
        if self.property("selected") == selected:
            return
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
    
    def mousePressEvent(self, event) -> None:
        """Handle mouse press to allow item selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
    
    def _on_delete_clicked(self) -> None:
        """Handle delete button click."""
        self.delete_requested.emit(self._chat_id, self._title)


class Sidebar(QFrame):
    """Sidebar widget for workspace and chat navigation."""
    
    chat_selected = Signal(str)  # chat_id
    new_chat_requested = Signal()
    memory_panel_requested = Signal()
    knowledge_base_requested = Signal()  # open KB folder
    deep_research_requested = Signal()  # For future use
    settings_requested = Signal()
    
    def __init__(
        self,
        viewmodel: WorkspaceViewModel,
        memory_viewmodel: Optional[WorkspaceMemoryViewModel] = None,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the sidebar.
        
        Args:
            viewmodel: The workspace viewmodel.
            memory_viewmodel: Workspace memory viewmodel.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.viewmodel = viewmodel
        self.memory_viewmodel = memory_viewmodel
        self.setObjectName("sidebar")
        self.setFixedWidth(300)
        self._setup_ui()
        self._connect_signals()
        self._refresh()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 1. Top Section: Workspace & Brand
        top_container = QWidget()
        top_layout = QVBoxLayout(top_container)
        top_layout.setContentsMargins(16, 0, 16, 0)
        top_layout.setSpacing(0)
        
        # Workspace selector row (match chat header height for alignment)
        workspace_row_container = QWidget()
        workspace_row_container.setFixedHeight(64)
        workspace_row = QHBoxLayout(workspace_row_container)
        workspace_row.setContentsMargins(0, 0, 0, 0)
        workspace_row.setSpacing(8)
        
        self._workspace_combo = QComboBox()
        self._workspace_combo.setObjectName("cleanCombo")
        self._workspace_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        workspace_row.addWidget(self._workspace_combo, 1, Qt.AlignmentFlag.AlignVCenter)
        
        self._new_workspace_btn = QPushButton("+")
        self._new_workspace_btn.setFixedSize(32, 32)
        action_btn_style = "font-size: 18px; font-weight: 700; padding: 0px;"
        self._new_workspace_btn.setStyleSheet(action_btn_style)
        self._new_workspace_btn.setObjectName("iconButton")
        # self._new_workspace_btn.setToolTip("New Workspace") # Avoiding tooltip default styles for now
        workspace_row.addWidget(self._new_workspace_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        self._delete_workspace_btn = QPushButton("-")
        self._delete_workspace_btn.setFixedSize(32, 32)
        self._delete_workspace_btn.setStyleSheet(action_btn_style)
        #self._delete_workspace_btn = QPushButton("Delete Workspace")
        self._delete_workspace_btn.setObjectName("iconButton")
        workspace_row.addWidget(self._delete_workspace_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        
        top_layout.addWidget(workspace_row_container)
        
        # Logo placeholder
        logo_path = (
            Path(__file__).resolve().parents[1]
            / "assets"
            / "icons"
            / "Logo.png"
        )
        
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setFixedHeight(150)
        
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            if not pixmap.isNull():
                # Scale to fit height, keeping aspect ratio
                scaled_pixmap = pixmap.scaled(
                    QSize(300, 150), # Width arbitrary sufficient, height constrained
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                logo_label.setPixmap(scaled_pixmap)
            else:
                logo_label.setText("LOGO ERROR")
        else:
             logo_label.setText("LOGO NOT FOUND")

        top_layout.addWidget(logo_label)

        # Status Label (Moved from Main Window)
        self._status_label = QLabel("Ready")
        self._status_label.setObjectName("statusLabel")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet("color: #6B7280; font-family: monospace; font-size: 11px; padding-bottom: 8px;")
        top_layout.addWidget(self._status_label)
        
        layout.addWidget(top_container)
        
        # 2. Previous Sessions (Chat List)
        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(16, 16, 16, 8)
        list_layout.setSpacing(8)
        
        # Header
        list_header = QHBoxLayout()
        list_header.setContentsMargins(0, 0, 5, 0)
        chats_label = QLabel("PREVIOUS SESSIONS")
        chats_label.setObjectName("sectionLabel")
        list_header.addWidget(chats_label)
        list_header.addStretch()
        
        # New Chat Icon Button
        self._new_chat_btn = QPushButton("+")
        self._new_chat_btn.setObjectName("iconButton")
        self._new_chat_btn.setToolTip("New Chat")

        action_btn_style = "font-size: 18px; font-weight: 700; padding: 0px;"
        self._new_chat_btn.setStyleSheet(action_btn_style)


        self._new_chat_btn.setFixedSize(32, 32)
        list_header.addWidget(self._new_chat_btn)

        list_layout.addLayout(list_header)
        
        # Chat List
        self._chat_list = QListWidget()
        self._chat_list.setObjectName("chatList")
        self._chat_list.setSpacing(4)
        self._chat_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        list_layout.addWidget(self._chat_list)
        
        layout.addWidget(list_container, 1) # Stretch
        
        # 3. Bottom Cards
        cards_container = QWidget()
        cards_layout = QVBoxLayout(cards_container)
        cards_layout.setContentsMargins(16, 0, 16, 16)
        cards_layout.setSpacing(12)
        
        # Knowledge Base & Deep Research Icon Buttons (side by side)
        icon_buttons_row = QHBoxLayout()
        icon_buttons_row.setSpacing(12)
        
        # Icon paths
        kb_icon_path = (
            Path(__file__).resolve().parents[1]
            / "assets"
            / "icons"
            / "KNOWLEDGE_BASE.svg"
        )
        deep_icon_path = (
            Path(__file__).resolve().parents[1]
            / "assets"
            / "icons"
            / "DEEP_RESEARCH.svg"
        )
        
        # Knowledge Base Button
        self._kb_btn = QPushButton()
        self._kb_btn.setObjectName("iconButton")
        self._kb_btn.setToolTip("Knowledge Base")
        self._kb_btn.setFixedSize(48, 48)
        self._kb_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._kb_icon_path = kb_icon_path
        self._kb_icon_size = QSize(24, 24)
        if kb_icon_path.exists():
            self._kb_btn.setIcon(QIcon(str(kb_icon_path)))
            self._kb_btn.setIconSize(self._kb_icon_size)
        
        # Deep Research Button
        self._deep_btn = QPushButton()
        self._deep_btn.setObjectName("iconButton")
        self._deep_btn.setToolTip("Deep Research")
        self._deep_btn.setFixedSize(48, 48)
        self._deep_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._deep_icon_path = deep_icon_path
        self._deep_icon_size = QSize(24, 24)
        if deep_icon_path.exists():
            self._deep_btn.setIcon(QIcon(str(deep_icon_path)))
            self._deep_btn.setIconSize(self._deep_icon_size)
        
        # Hidden label for RAG status (kept for API compatibility)
        self._rag_status_label = QLabel("")
        self._rag_status_label.setVisible(False)
        
        icon_buttons_row.addStretch()
        icon_buttons_row.addWidget(self._kb_btn)
        icon_buttons_row.addWidget(self._deep_btn)
        icon_buttons_row.addStretch()
        
        cards_layout.addLayout(icon_buttons_row)
        
        # Settings Button (Centered at bottom)
        settings_container = QHBoxLayout()
        settings_container.addStretch()
        self._settings_btn = QPushButton()
        self._settings_icon_path = (
            Path(__file__).resolve().parents[1]
            / "assets"
            / "icons"
            / "settings.svg"
        )
        self._settings_icon_size = QSize(18, 18)
        self._settings_btn.setIcon(QIcon(str(self._settings_icon_path)))
        self._settings_btn.setIconSize(self._settings_icon_size)
        self._settings_btn.setObjectName("settingsButton")
        self._settings_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        settings_container.addWidget(self._settings_btn)
        settings_container.addStretch()
        
        cards_layout.addLayout(settings_container)
        
        layout.addWidget(cards_container)

    
    def _connect_signals(self) -> None:
        """Connect signals to slots."""
        # ViewModel signals
        self.viewmodel.workspaces_changed.connect(self._refresh_workspaces)
        self.viewmodel.chats_changed.connect(self._refresh_chats)
        self.viewmodel.current_workspace_changed.connect(self._on_workspace_changed)
        self.viewmodel.current_chat_changed.connect(self._on_chat_changed)


        # UI signals
        self._workspace_combo.currentIndexChanged.connect(
            self._on_workspace_combo_changed
        )
        self._new_workspace_btn.clicked.connect(self._on_new_workspace)
        self._new_chat_btn.clicked.connect(self._on_new_chat)
        self._chat_list.currentItemChanged.connect(self._on_chat_list_changed)
        self._delete_workspace_btn.clicked.connect(self._on_delete_workspace)

        self._kb_btn.clicked.connect(self.knowledge_base_requested.emit)
        self._deep_btn.clicked.connect(self.deep_research_requested.emit)
        self._settings_btn.clicked.connect(self.settings_requested.emit)

    def apply_theme(self, mode) -> None:
        """Apply theme-aware visuals."""
        self._apply_settings_icon(mode)
        self._apply_icon_buttons_theme(mode)

    def _apply_icon_buttons_theme(self, mode) -> None:
        """Update KB and Deep Research icon colors for the active theme."""
        from ..core.models import ThemeMode
        from .styles import COLORS

        c = COLORS["dark"] if mode == ThemeMode.DARK else COLORS["light"]
        normal_color = c["text_muted"]
        active_color = COLORS["primary"]

        # Knowledge Base icon
        if self._kb_icon_path.exists():
            base_icon = QIcon(str(self._kb_icon_path))
            tinted = self._build_tinted_icon(
                base_icon,
                normal_color,
                active_color,
                self._kb_icon_size,
            )
            self._kb_btn.setIcon(tinted)

        # Deep Research icon
        if self._deep_icon_path.exists():
            base_icon = QIcon(str(self._deep_icon_path))
            tinted = self._build_tinted_icon(
                base_icon,
                normal_color,
                active_color,
                self._deep_icon_size,
            )
            self._deep_btn.setIcon(tinted)

    def _apply_settings_icon(self, mode) -> None:
        """Update settings icon colors for the active theme."""
        from ..core.models import ThemeMode
        from .styles import COLORS

        if not self._settings_icon_path.exists():
            self._settings_btn.setIcon(QIcon())
            return

        c = COLORS["dark"] if mode == ThemeMode.DARK else COLORS["light"]
        normal_color = c["text_muted"]
        active_color = COLORS["primary"]
        base_icon = QIcon(str(self._settings_icon_path))
        tinted = self._build_tinted_icon(
            base_icon,
            normal_color,
            active_color,
            self._settings_icon_size,
        )
        self._settings_btn.setIcon(tinted)

    @staticmethod
    def _build_tinted_icon(
        base_icon: QIcon,
        normal_color: str,
        active_color: str,
        size: QSize,
    ) -> QIcon:
        icon = QIcon()
        normal_pixmap = Sidebar._tint_pixmap(base_icon, normal_color, size)
        if not normal_pixmap.isNull():
            icon.addPixmap(normal_pixmap, QIcon.Mode.Normal, QIcon.State.Off)
        active_pixmap = Sidebar._tint_pixmap(base_icon, active_color, size)
        if not active_pixmap.isNull():
            icon.addPixmap(active_pixmap, QIcon.Mode.Active, QIcon.State.Off)
            icon.addPixmap(active_pixmap, QIcon.Mode.Selected, QIcon.State.Off)
        return icon

    @staticmethod
    def _tint_pixmap(icon: QIcon, color: str, size: QSize) -> QPixmap:
        pixmap = icon.pixmap(size)
        if pixmap.isNull():
            return QPixmap()
        tinted = QPixmap(pixmap.size())
        tinted.setDevicePixelRatio(pixmap.devicePixelRatio())
        tinted.fill(Qt.transparent)
        painter = QPainter(tinted)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), QColor(color))
        painter.end()
        return tinted
    
    def _refresh(self) -> None:
        """Refresh all data."""
        self._refresh_workspaces()
        self._refresh_chats()
    
    def _refresh_workspaces(self) -> None:
        """Refresh the workspace dropdown."""
        self._workspace_combo.blockSignals(True)
        self._workspace_combo.clear()
        
        for workspace in self.viewmodel.workspaces:
            self._workspace_combo.addItem(workspace.name, workspace.id)
        
        # Select current workspace
        current = self.viewmodel.current_workspace
        if current:
            index = self._workspace_combo.findData(current.id)
            if index >= 0:
                self._workspace_combo.setCurrentIndex(index)
        
        self._workspace_combo.blockSignals(False)
    
    def _refresh_chats(self) -> None:
        """Refresh the chat list."""
        self._chat_list.blockSignals(True)
        self._chat_list.clear()
        
        for chat in self.viewmodel.chats:
            display_title = chat.title[:30] + ("..." if len(chat.title) > 30 else "")
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, chat.id)
            item.setToolTip(chat.title)
            self._chat_list.addItem(item)
            
            item_widget = ChatListItemWidget(
                chat.id,
                chat.title,
                display_title,
            )
            item_widget.clicked.connect(
                lambda list_item=item: self._chat_list.setCurrentItem(list_item)
            )
            item_widget.delete_requested.connect(self._on_delete_chat_requested)
            item.setSizeHint(item_widget.sizeHint())
            self._chat_list.setItemWidget(item, item_widget)
        
        # Select current chat
        current = self.viewmodel.current_chat
        if current:
            for i in range(self._chat_list.count()):
                item = self._chat_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == current.id:
                    self._chat_list.setCurrentItem(item)
                    break
        
        self._chat_list.blockSignals(False)
        self._sync_chat_item_selection()
    
    def _on_workspace_changed(self) -> None:
        """Handle workspace change from viewmodel."""
        self._refresh_workspaces()
    
    def _on_chat_changed(self) -> None:
        """Handle chat change from viewmodel."""
        current = self.viewmodel.current_chat
        if current:
            for i in range(self._chat_list.count()):
                item = self._chat_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == current.id:
                    self._chat_list.blockSignals(True)
                    self._chat_list.setCurrentItem(item)
                    self._chat_list.blockSignals(False)
                    break
        self._sync_chat_item_selection()


    
    def _on_workspace_combo_changed(self, index: int) -> None:
        """Handle workspace selection change."""
        if index < 0:
            return
        workspace_id = self._workspace_combo.itemData(index)
        if workspace_id:
            self.viewmodel.select_workspace(workspace_id)
    
    def _on_chat_list_changed(
        self,
        current: Optional[QListWidgetItem],
        previous: Optional[QListWidgetItem],
    ) -> None:
        """Handle chat selection change."""
        if current is None:
            self._sync_chat_item_selection()
            return
        chat_id = current.data(Qt.ItemDataRole.UserRole)
        if chat_id:
            self.viewmodel.select_chat(chat_id)
            self.chat_selected.emit(chat_id)
        self._sync_chat_item_selection()
    
    def _on_new_workspace(self) -> None:
        """Handle new workspace button click."""
        name, ok = QInputDialog.getText(
            self,
            "New Workspace",
            "Enter workspace name:",
        )
        if ok and name.strip():
            self.viewmodel.create_workspace(name.strip())
    
    def _on_new_chat(self) -> None:
        """Handle new chat button click."""
        self.new_chat_requested.emit()
    
    def _on_delete_workspace(self) -> None:
        """Handle delete workspace button click."""
        current = self.viewmodel.current_workspace
        if not current:
            return
        
        reply = QMessageBox.question(
            self,
            "Delete Workspace",
            f"Are you sure you want to delete '{current.name}' and all its chats?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.viewmodel.delete_workspace(current.id)

    def _on_delete_chat_requested(self, chat_id: str, chat_title: str) -> None:
        """Handle delete chat button click."""
        self._confirm_delete_chat(chat_id, chat_title)
    
    def delete_current_chat(self) -> None:
        """Delete the currently selected chat."""
        current = self.viewmodel.current_chat
        if not current:
            return
        
        self._confirm_delete_chat(current.id, current.title)
    
    def _confirm_delete_chat(self, chat_id: str, chat_title: str) -> None:
        """Confirm chat deletion and remove it."""
        reply = QMessageBox.question(
            self,
            "Delete Chat",
            f"Are you sure you want to delete '{chat_title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.viewmodel.delete_chat(chat_id)

    def _sync_chat_item_selection(self) -> None:
        """Sync item selection styling with the current item."""
        current_item = self._chat_list.currentItem()
        for i in range(self._chat_list.count()):
            item = self._chat_list.item(i)
            widget = self._chat_list.itemWidget(item)
            if isinstance(widget, ChatListItemWidget):
                widget.set_selected(item == current_item)
    
    def update_rag_status(self, is_ready: bool, status_text: str = "") -> None:
        """Update the RAG status display.
        
        Args:
            is_ready: Whether RAG is ready for queries.
            status_text: Optional status text to display.
        """
        # We update the subtitle of the KB button now
        if status_text:
             self._rag_status_label.setText(status_text)
        elif is_ready:
            self._rag_status_label.setText("Review Indexed Files")
        else:
            self._rag_status_label.setText("Not Indexed / Open Folder")

    def set_status(self, message: str) -> None:
        """Update the status label text.
        
        Args:
            message: The status message to display.
        """
        self._status_label.setText(message)
