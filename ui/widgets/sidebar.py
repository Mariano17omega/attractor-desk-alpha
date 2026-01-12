"""Sidebar widget for workspace and session navigation."""

from __future__ import annotations

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

from core.models import ThemeMode
from ui.viewmodels.workspace_viewmodel import WorkspaceViewModel
from ui.styles import COLORS


class SessionListItemWidget(QFrame):
    """Widget for a session list item with a delete button."""

    clicked = Signal()
    delete_requested = Signal(str, str)

    def __init__(
        self,
        session_id: str,
        title: str,
        display_title: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._session_id = session_id
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
        self._delete_btn.setToolTip("Delete session")
        self._delete_btn.setFixedSize(32, 32)
        self._delete_btn.setStyleSheet("font-size: 18px; font-weight: 700; padding: 0px;")
        self._delete_btn.clicked.connect(self._on_delete_clicked)
        layout.addWidget(self._delete_btn)

    def set_selected(self, selected: bool) -> None:
        if self.property("selected") == selected:
            return
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def _on_delete_clicked(self) -> None:
        self.delete_requested.emit(self._session_id, self._title)


class Sidebar(QFrame):
    """Sidebar widget for workspace and session navigation."""

    session_selected = Signal(str)
    new_session_requested = Signal()
    knowledge_base_requested = Signal()
    deep_research_requested = Signal()
    settings_requested = Signal()

    def __init__(
        self,
        viewmodel: WorkspaceViewModel,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.viewmodel = viewmodel
        self.setObjectName("sidebar")
        self.setFixedWidth(300)
        self._setup_ui()
        self._connect_signals()
        self._refresh()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        top_container = QWidget()
        top_layout = QVBoxLayout(top_container)
        top_layout.setContentsMargins(16, 0, 16, 0)
        top_layout.setSpacing(0)

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
        self._new_workspace_btn.setStyleSheet("font-size: 18px; font-weight: 700; padding: 0px;")
        self._new_workspace_btn.setObjectName("iconButton")
        workspace_row.addWidget(self._new_workspace_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        self._delete_workspace_btn = QPushButton("-")
        self._delete_workspace_btn.setFixedSize(32, 32)
        self._delete_workspace_btn.setStyleSheet("font-size: 18px; font-weight: 700; padding: 0px;")
        self._delete_workspace_btn.setObjectName("iconButton")
        workspace_row.addWidget(self._delete_workspace_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        top_layout.addWidget(workspace_row_container)

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
                scaled_pixmap = pixmap.scaled(
                    QSize(300, 150),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                logo_label.setPixmap(scaled_pixmap)
            else:
                logo_label.setText("LOGO ERROR")
        else:
            logo_label.setText("LOGO NOT FOUND")

        top_layout.addWidget(logo_label)

        self._status_label = QLabel("Ready")
        self._status_label.setObjectName("statusLabel")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet(
            "color: #6B7280; font-family: monospace; font-size: 11px; padding-bottom: 8px;"
        )
        top_layout.addWidget(self._status_label)

        layout.addWidget(top_container)

        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(16, 16, 16, 8)
        list_layout.setSpacing(8)

        list_header = QHBoxLayout()
        list_header.setContentsMargins(0, 0, 5, 0)
        sessions_label = QLabel("PREVIOUS SESSIONS")
        sessions_label.setObjectName("sectionLabel")
        list_header.addWidget(sessions_label)
        list_header.addStretch()

        self._new_session_btn = QPushButton("+")
        self._new_session_btn.setObjectName("iconButton")
        self._new_session_btn.setToolTip("New Session")
        self._new_session_btn.setStyleSheet("font-size: 18px; font-weight: 700; padding: 0px;")
        self._new_session_btn.setFixedSize(32, 32)
        list_header.addWidget(self._new_session_btn)

        list_layout.addLayout(list_header)

        self._session_list = QListWidget()
        self._session_list.setObjectName("chatList")
        self._session_list.setSpacing(4)
        self._session_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        list_layout.addWidget(self._session_list)

        layout.addWidget(list_container, 1)

        cards_container = QWidget()
        cards_layout = QVBoxLayout(cards_container)
        cards_layout.setContentsMargins(16, 0, 16, 16)
        cards_layout.setSpacing(12)

        icon_buttons_row = QHBoxLayout()
        icon_buttons_row.setSpacing(12)

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

        icon_buttons_row.addStretch()
        icon_buttons_row.addWidget(self._kb_btn)
        icon_buttons_row.addWidget(self._deep_btn)
        icon_buttons_row.addStretch()

        cards_layout.addLayout(icon_buttons_row)

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
        if self._settings_icon_path.exists():
            self._settings_btn.setIcon(QIcon(str(self._settings_icon_path)))
            self._settings_btn.setIconSize(self._settings_icon_size)
        self._settings_btn.setObjectName("settingsButton")
        self._settings_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        settings_container.addWidget(self._settings_btn)
        settings_container.addStretch()

        cards_layout.addLayout(settings_container)
        layout.addWidget(cards_container)

    def _connect_signals(self) -> None:
        self.viewmodel.workspaces_changed.connect(self._refresh_workspaces)
        self.viewmodel.sessions_changed.connect(self._refresh_sessions)
        self.viewmodel.current_workspace_changed.connect(self._on_workspace_changed)
        self.viewmodel.current_session_changed.connect(self._on_session_changed)

        self._workspace_combo.currentIndexChanged.connect(
            self._on_workspace_combo_changed
        )
        self._new_workspace_btn.clicked.connect(self._on_new_workspace)
        self._delete_workspace_btn.clicked.connect(self._on_delete_workspace)
        self._new_session_btn.clicked.connect(self._on_new_session)
        self._session_list.currentItemChanged.connect(self._on_session_list_changed)

        self._kb_btn.clicked.connect(self.knowledge_base_requested.emit)
        self._deep_btn.clicked.connect(self.deep_research_requested.emit)
        self._settings_btn.clicked.connect(self.settings_requested.emit)

    def apply_theme(self, mode: ThemeMode) -> None:
        self._apply_settings_icon(mode)
        self._apply_icon_buttons_theme(mode)

    def _apply_icon_buttons_theme(self, mode: ThemeMode) -> None:
        c = COLORS["dark"] if mode == ThemeMode.DARK else COLORS["light"]
        normal_color = c["text_muted"]
        active_color = COLORS["primary"]

        if self._kb_icon_path.exists():
            base_icon = QIcon(str(self._kb_icon_path))
            tinted = self._build_tinted_icon(
                base_icon,
                normal_color,
                active_color,
                self._kb_icon_size,
            )
            self._kb_btn.setIcon(tinted)

        if self._deep_icon_path.exists():
            base_icon = QIcon(str(self._deep_icon_path))
            tinted = self._build_tinted_icon(
                base_icon,
                normal_color,
                active_color,
                self._deep_icon_size,
            )
            self._deep_btn.setIcon(tinted)

    def _apply_settings_icon(self, mode: ThemeMode) -> None:
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
        self._refresh_workspaces()
        self._refresh_sessions()

    def _refresh_workspaces(self) -> None:
        self._workspace_combo.blockSignals(True)
        self._workspace_combo.clear()
        for workspace in self.viewmodel.workspaces:
            self._workspace_combo.addItem(workspace.name, workspace.id)

        current = self.viewmodel.current_workspace
        if current:
            index = self._workspace_combo.findData(current.id)
            if index >= 0:
                self._workspace_combo.setCurrentIndex(index)

        self._workspace_combo.blockSignals(False)

    def _refresh_sessions(self) -> None:
        self._session_list.blockSignals(True)
        self._session_list.clear()

        for session in self.viewmodel.sessions:
            display_title = session.title[:30] + ("..." if len(session.title) > 30 else "")
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, session.id)
            item.setToolTip(session.title)
            self._session_list.addItem(item)

            item_widget = SessionListItemWidget(
                session.id,
                session.title,
                display_title,
            )
            item_widget.clicked.connect(
                lambda list_item=item: self._session_list.setCurrentItem(list_item)
            )
            item_widget.delete_requested.connect(self._on_delete_session_requested)
            item.setSizeHint(item_widget.sizeHint())
            self._session_list.setItemWidget(item, item_widget)

        current = self.viewmodel.current_session
        if current:
            for i in range(self._session_list.count()):
                item = self._session_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == current.id:
                    self._session_list.setCurrentItem(item)
                    break

        self._session_list.blockSignals(False)
        self._sync_session_item_selection()

    def _on_workspace_changed(self) -> None:
        self._refresh_workspaces()

    def _on_session_changed(self) -> None:
        current = self.viewmodel.current_session
        if current:
            for i in range(self._session_list.count()):
                item = self._session_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == current.id:
                    self._session_list.blockSignals(True)
                    self._session_list.setCurrentItem(item)
                    self._session_list.blockSignals(False)
                    break
        self._sync_session_item_selection()

    def _sync_session_item_selection(self) -> None:
        current_item = self._session_list.currentItem()
        for i in range(self._session_list.count()):
            item = self._session_list.item(i)
            widget = self._session_list.itemWidget(item)
            if isinstance(widget, SessionListItemWidget):
                widget.set_selected(item == current_item)

    def _on_workspace_combo_changed(self, index: int) -> None:
        if index < 0:
            return
        workspace_id = self._workspace_combo.itemData(index)
        if workspace_id:
            self.viewmodel.select_workspace(workspace_id)

    def _on_new_workspace(self) -> None:
        name, ok = QInputDialog.getText(
            self,
            "New Workspace",
            "Enter workspace name:",
        )
        if ok and name.strip():
            self.viewmodel.create_workspace(name.strip())

    def _on_delete_workspace(self) -> None:
        current = self.viewmodel.current_workspace
        if not current:
            return
        confirm = QMessageBox.question(
            self,
            "Delete Workspace",
            f"Delete workspace '{current.name}' and all its sessions?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            self.viewmodel.delete_workspace(current.id)

    def _on_new_session(self) -> None:
        self.new_session_requested.emit()

    def _on_session_list_changed(
        self,
        current: Optional[QListWidgetItem],
        _previous: Optional[QListWidgetItem],
    ) -> None:
        if current is None:
            return
        session_id = current.data(Qt.ItemDataRole.UserRole)
        if session_id:
            self.viewmodel.select_session(session_id)
            self.session_selected.emit(session_id)
        self._sync_session_item_selection()

    def _on_delete_session_requested(self, session_id: str, title: str) -> None:
        confirm = QMessageBox.question(
            self,
            "Delete Session",
            f"Delete session '{title}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            self.viewmodel.delete_session(session_id)

    def set_status(self, message: str) -> None:
        self._status_label.setText(message)
