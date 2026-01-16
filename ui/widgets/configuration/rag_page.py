"""RAG settings page."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.viewmodels.settings_viewmodel import SettingsViewModel


class RagPage(QWidget):
    """Settings page for local RAG configuration."""

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

        title = QLabel("RAG Settings")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        description = QLabel(
            "Configure local retrieval-augmented generation using your stored artifacts. "
            "Retrieval runs only when enabled and when a question needs grounded context."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #6c7086; margin-bottom: 16px;")
        layout.addWidget(description)

        self._enabled_check = QCheckBox("Enable RAG retrieval")
        self._enabled_check.setStyleSheet("font-weight: 500;")
        layout.addWidget(self._enabled_check)

        self._index_text_check = QCheckBox("Index text artifacts on save")
        self._index_text_check.setToolTip("PDF imports are always indexed.")
        layout.addWidget(self._index_text_check)

        scope_row = QHBoxLayout()
        scope_label = QLabel("Retrieval Scope:")
        scope_label.setMinimumWidth(150)
        self._scope_session = QRadioButton("Session")
        self._scope_workspace = QRadioButton("Workspace")
        self._scope_global = QRadioButton("Global")
        self._scope_group = QButtonGroup(self)
        self._scope_group.addButton(self._scope_session, 0)
        self._scope_group.addButton(self._scope_workspace, 1)
        self._scope_group.addButton(self._scope_global, 2)
        scope_row.addWidget(scope_label)
        scope_row.addWidget(self._scope_session)
        scope_row.addWidget(self._scope_workspace)
        scope_row.addWidget(self._scope_global)
        scope_row.addStretch()
        layout.addLayout(scope_row)

        chunk_size_row = QHBoxLayout()
        chunk_size_label = QLabel("Chunk Size (chars):")
        chunk_size_label.setMinimumWidth(150)
        self._chunk_size_spin = QSpinBox()
        self._chunk_size_spin.setRange(200, 5000)
        self._chunk_size_spin.setSingleStep(100)
        self._chunk_size_spin.setMinimumWidth(100)
        chunk_size_row.addWidget(chunk_size_label)
        chunk_size_row.addWidget(self._chunk_size_spin)
        chunk_size_row.addStretch()
        layout.addLayout(chunk_size_row)

        chunk_overlap_row = QHBoxLayout()
        chunk_overlap_label = QLabel("Chunk Overlap (chars):")
        chunk_overlap_label.setMinimumWidth(150)
        self._chunk_overlap_spin = QSpinBox()
        self._chunk_overlap_spin.setRange(0, 1000)
        self._chunk_overlap_spin.setSingleStep(25)
        self._chunk_overlap_spin.setMinimumWidth(100)
        chunk_overlap_row.addWidget(chunk_overlap_label)
        chunk_overlap_row.addWidget(self._chunk_overlap_spin)
        chunk_overlap_row.addStretch()
        layout.addLayout(chunk_overlap_row)

        k_lex_row = QHBoxLayout()
        k_lex_label = QLabel("Lexical Results (K):")
        k_lex_label.setMinimumWidth(150)
        self._k_lex_spin = QSpinBox()
        self._k_lex_spin.setRange(1, 50)
        self._k_lex_spin.setMinimumWidth(80)
        k_lex_row.addWidget(k_lex_label)
        k_lex_row.addWidget(self._k_lex_spin)
        k_lex_row.addStretch()
        layout.addLayout(k_lex_row)

        k_vec_row = QHBoxLayout()
        k_vec_label = QLabel("Vector Results (K):")
        k_vec_label.setMinimumWidth(150)
        self._k_vec_spin = QSpinBox()
        self._k_vec_spin.setRange(0, 50)
        self._k_vec_spin.setMinimumWidth(80)
        k_vec_row.addWidget(k_vec_label)
        k_vec_row.addWidget(self._k_vec_spin)
        k_vec_row.addStretch()
        layout.addLayout(k_vec_row)

        rrf_row = QHBoxLayout()
        rrf_label = QLabel("RRF K:")
        rrf_label.setMinimumWidth(150)
        self._rrf_spin = QSpinBox()
        self._rrf_spin.setRange(10, 200)
        self._rrf_spin.setMinimumWidth(80)
        rrf_row.addWidget(rrf_label)
        rrf_row.addWidget(self._rrf_spin)
        rrf_row.addStretch()
        layout.addLayout(rrf_row)

        max_candidates_row = QHBoxLayout()
        max_candidates_label = QLabel("Max Candidates:")
        max_candidates_label.setMinimumWidth(150)
        self._max_candidates_spin = QSpinBox()
        self._max_candidates_spin.setRange(1, 50)
        self._max_candidates_spin.setMinimumWidth(80)
        max_candidates_row.addWidget(max_candidates_label)
        max_candidates_row.addWidget(self._max_candidates_spin)
        max_candidates_row.addStretch()
        layout.addLayout(max_candidates_row)

        embedding_row = QHBoxLayout()
        embedding_label = QLabel("Embedding Model:")
        embedding_label.setMinimumWidth(150)
        self._embedding_input = QLineEdit()
        self._embedding_input.setPlaceholderText("openai/text-embedding-3-small")
        self._embedding_input.setMinimumWidth(300)
        self._embedding_input.setMaximumWidth(500)
        embedding_row.addWidget(embedding_label)
        embedding_row.addWidget(self._embedding_input)
        embedding_row.addStretch()
        layout.addLayout(embedding_row)

        self._query_rewrite_check = QCheckBox("Enable query rewrite")
        self._llm_rerank_check = QCheckBox("Enable LLM rerank")
        layout.addWidget(self._query_rewrite_check)
        layout.addWidget(self._llm_rerank_check)

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

        info_title = QLabel("ℹ️  Local RAG Notes")
        info_title.setStyleSheet("font-weight: bold; color: #cdd6f4;")
        info_layout.addWidget(info_title)

        info_text = QLabel(
            "• PDF imports are indexed automatically\n"
            "• Vector retrieval requires an embedding model\n"
            "• LLM rerank increases latency and cost"
        )
        info_text.setStyleSheet("color: #a6adc8; line-height: 1.5;")
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)

        layout.addWidget(info_container)

        global_title = QLabel("Global RAG Library")
        global_title.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 16px;")
        layout.addWidget(global_title)

        folder_row = QHBoxLayout()
        folder_label = QLabel("Global Folder:")
        folder_label.setMinimumWidth(150)
        self._global_folder_input = QLineEdit()
        self._global_folder_input.setPlaceholderText("~/Documents/AttractorDeskRAG")
        self._global_folder_button = QPushButton("Browse")
        folder_row.addWidget(folder_label)
        folder_row.addWidget(self._global_folder_input)
        folder_row.addWidget(self._global_folder_button)
        layout.addLayout(folder_row)

        self._global_monitor_check = QCheckBox("Automatic monitoring")
        layout.addWidget(self._global_monitor_check)

        action_row = QHBoxLayout()
        self._global_scan_button = QPushButton("Check for new PDFs")
        self._global_index_button = QPushButton("Index all PDFs")
        action_row.addWidget(self._global_scan_button)
        action_row.addWidget(self._global_index_button)
        action_row.addStretch()
        layout.addLayout(action_row)

        status_row = QHBoxLayout()
        self._global_status_label = QLabel("Idle")
        self._global_status_label.setStyleSheet("color: #6c7086;")
        self._global_progress = QProgressBar()
        self._global_progress.setRange(0, 1)
        self._global_progress.setValue(0)
        status_row.addWidget(self._global_status_label)
        status_row.addWidget(self._global_progress)
        layout.addLayout(status_row)

        filter_row = QHBoxLayout()
        filter_label = QLabel("Document Status:")
        filter_label.setMinimumWidth(150)
        self._global_status_filter = QComboBox()
        self._global_status_filter.addItems(["All", "indexed", "indexing", "error"])
        self._global_refresh_button = QPushButton("Refresh")
        filter_row.addWidget(filter_label)
        filter_row.addWidget(self._global_status_filter)
        filter_row.addWidget(self._global_refresh_button)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        self._global_docs_table = QTableWidget(0, 5)
        self._global_docs_table.setHorizontalHeaderLabels(
            ["Name", "Path", "Status", "Indexed At", "Embedding"]
        )
        header = self._global_docs_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._global_docs_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._global_docs_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self._global_docs_table)

        cleanup_title = QLabel("ChatPDF Cleanup")
        cleanup_title.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 16px;")
        layout.addWidget(cleanup_title)

        retention_row = QHBoxLayout()
        retention_label = QLabel("Retention (days):")
        retention_label.setMinimumWidth(150)
        self._retention_spin = QSpinBox()
        self._retention_spin.setRange(1, 90)
        retention_row.addWidget(retention_label)
        retention_row.addWidget(self._retention_spin)
        retention_row.addStretch()
        layout.addLayout(retention_row)

        cleanup_row = QHBoxLayout()
        self._cleanup_button = QPushButton("Clean old session PDFs")
        self._cleanup_status = QLabel("")
        self._cleanup_status.setStyleSheet("color: #6c7086;")
        cleanup_row.addWidget(self._cleanup_button)
        cleanup_row.addWidget(self._cleanup_status)
        cleanup_row.addStretch()
        layout.addLayout(cleanup_row)
        layout.addStretch()

    def _load_values(self) -> None:
        self._enabled_check.setChecked(self._viewmodel.rag_enabled)
        self._index_text_check.setChecked(self._viewmodel.rag_index_text_artifacts)
        if self._viewmodel.rag_scope == "global":
            self._scope_global.setChecked(True)
        elif self._viewmodel.rag_scope == "workspace":
            self._scope_workspace.setChecked(True)
        else:
            self._scope_session.setChecked(True)
        self._chunk_size_spin.setValue(self._viewmodel.rag_chunk_size_chars)
        self._chunk_overlap_spin.setValue(self._viewmodel.rag_chunk_overlap_chars)
        self._k_lex_spin.setValue(self._viewmodel.rag_k_lex)
        self._k_vec_spin.setValue(self._viewmodel.rag_k_vec)
        self._rrf_spin.setValue(self._viewmodel.rag_rrf_k)
        self._max_candidates_spin.setValue(self._viewmodel.rag_max_candidates)
        self._embedding_input.setText(self._viewmodel.rag_embedding_model)
        self._query_rewrite_check.setChecked(self._viewmodel.rag_enable_query_rewrite)
        self._llm_rerank_check.setChecked(self._viewmodel.rag_enable_llm_rerank)
        self._global_folder_input.setText(self._viewmodel.rag_global_folder)
        self._global_monitor_check.setChecked(self._viewmodel.rag_global_monitoring_enabled)
        self._retention_spin.setValue(self._viewmodel.rag_chatpdf_retention_days)
        self._refresh_registry_table()

    def _connect_signals(self) -> None:
        self._enabled_check.toggled.connect(self._on_enabled_changed)
        self._index_text_check.toggled.connect(self._on_index_text_changed)
        self._scope_group.buttonClicked.connect(self._on_scope_changed)
        self._chunk_size_spin.valueChanged.connect(self._on_chunk_size_changed)
        self._chunk_overlap_spin.valueChanged.connect(self._on_chunk_overlap_changed)
        self._k_lex_spin.valueChanged.connect(self._on_k_lex_changed)
        self._k_vec_spin.valueChanged.connect(self._on_k_vec_changed)
        self._rrf_spin.valueChanged.connect(self._on_rrf_changed)
        self._max_candidates_spin.valueChanged.connect(self._on_max_candidates_changed)
        self._embedding_input.textChanged.connect(self._on_embedding_model_changed)
        self._query_rewrite_check.toggled.connect(self._on_query_rewrite_changed)
        self._llm_rerank_check.toggled.connect(self._on_llm_rerank_changed)
        self._global_folder_button.clicked.connect(self._on_global_folder_browse)
        self._global_folder_input.textChanged.connect(self._on_global_folder_changed)
        self._global_monitor_check.toggled.connect(self._on_global_monitor_changed)
        self._global_scan_button.clicked.connect(self._on_global_scan)
        self._global_index_button.clicked.connect(self._on_global_index)
        self._global_refresh_button.clicked.connect(self._refresh_registry_table)
        self._global_status_filter.currentTextChanged.connect(self._refresh_registry_table)
        self._viewmodel.global_rag_progress.connect(self._on_global_progress)
        self._viewmodel.global_rag_complete.connect(self._on_global_complete)
        self._viewmodel.global_rag_error.connect(self._on_global_error)
        self._viewmodel.global_rag_registry_updated.connect(self._refresh_registry_table)
        self._retention_spin.valueChanged.connect(self._on_retention_changed)
        self._cleanup_button.clicked.connect(self._on_cleanup_clicked)
        self._viewmodel.chatpdf_cleanup_complete.connect(self._on_cleanup_complete)

    def _on_enabled_changed(self, checked: bool) -> None:
        self._viewmodel.rag_enabled = checked

    def _on_index_text_changed(self, checked: bool) -> None:
        self._viewmodel.rag_index_text_artifacts = checked

    def _on_scope_changed(self) -> None:
        if self._scope_global.isChecked():
            self._viewmodel.rag_scope = "global"
        elif self._scope_workspace.isChecked():
            self._viewmodel.rag_scope = "workspace"
        else:
            self._viewmodel.rag_scope = "session"

    def _on_chunk_size_changed(self, value: int) -> None:
        self._viewmodel.rag_chunk_size_chars = value

    def _on_chunk_overlap_changed(self, value: int) -> None:
        self._viewmodel.rag_chunk_overlap_chars = value

    def _on_k_lex_changed(self, value: int) -> None:
        self._viewmodel.rag_k_lex = value

    def _on_k_vec_changed(self, value: int) -> None:
        self._viewmodel.rag_k_vec = value

    def _on_rrf_changed(self, value: int) -> None:
        self._viewmodel.rag_rrf_k = value

    def _on_max_candidates_changed(self, value: int) -> None:
        self._viewmodel.rag_max_candidates = value

    def _on_embedding_model_changed(self, text: str) -> None:
        self._viewmodel.rag_embedding_model = text

    def _on_query_rewrite_changed(self, checked: bool) -> None:
        self._viewmodel.rag_enable_query_rewrite = checked

    def _on_llm_rerank_changed(self, checked: bool) -> None:
        self._viewmodel.rag_enable_llm_rerank = checked

    def _on_global_folder_browse(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "Select Global RAG Folder",
            self._global_folder_input.text() or str(Path.home()),
        )
        if selected:
            self._global_folder_input.setText(selected)

    def _on_global_folder_changed(self, text: str) -> None:
        self._viewmodel.rag_global_folder = text

    def _on_global_monitor_changed(self, checked: bool) -> None:
        self._viewmodel.rag_global_monitoring_enabled = checked

    def _on_global_scan(self) -> None:
        self._global_status_label.setText("Scanning for new PDFs...")
        self._viewmodel.scan_global_folder()

    def _on_global_index(self) -> None:
        self._global_status_label.setText("Indexing all PDFs...")
        self._viewmodel.start_global_index(force_reindex=True)

    def _on_global_progress(self, current: int, total: int, path: str) -> None:
        self._global_progress.setRange(0, max(total, 1))
        self._global_progress.setValue(current)
        self._global_status_label.setText(
            f"Indexing {current}/{total}: {Path(path).name}"
        )

    def _on_global_complete(self, result: object) -> None:
        indexed = getattr(result, "indexed", 0)
        skipped = getattr(result, "skipped", 0)
        failed = getattr(result, "failed", 0)
        self._global_status_label.setText(
            f"Indexed {indexed}, skipped {skipped}, failed {failed}"
        )
        self._global_progress.setValue(0)

    def _on_global_error(self, error: str) -> None:
        self._global_status_label.setText(f"Error: {error}")

    def _refresh_registry_table(self) -> None:
        filter_value = self._global_status_filter.currentText().strip()
        status = None if filter_value == "All" else filter_value
        entries = self._viewmodel.list_global_registry_entries(status=status)
        self._global_docs_table.setRowCount(0)
        for entry in entries:
            row = self._global_docs_table.rowCount()
            self._global_docs_table.insertRow(row)
            name = Path(entry.source_path).name
            indexed_at = entry.last_indexed_at.isoformat() if entry.last_indexed_at else ""
            embedding = entry.embedding_model or ""
            self._global_docs_table.setItem(row, 0, QTableWidgetItem(name))
            self._global_docs_table.setItem(row, 1, QTableWidgetItem(entry.source_path))
            self._global_docs_table.setItem(row, 2, QTableWidgetItem(entry.status))
            self._global_docs_table.setItem(row, 3, QTableWidgetItem(indexed_at))
            self._global_docs_table.setItem(row, 4, QTableWidgetItem(embedding))

    def _on_retention_changed(self, value: int) -> None:
        self._viewmodel.rag_chatpdf_retention_days = value

    def _on_cleanup_clicked(self) -> None:
        removed = self._viewmodel.cleanup_chatpdf_documents()
        self._cleanup_status.setText(f"Removed {removed} documents")

    def _on_cleanup_complete(self, removed: int) -> None:
        self._cleanup_status.setText(f"Removed {removed} documents")
