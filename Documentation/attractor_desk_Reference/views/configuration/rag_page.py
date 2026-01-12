"""RAG settings page for configuration."""

import os
import subprocess
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Signal, Slot, Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...viewmodels import SettingsViewModel
from ...infrastructure import RagService


class RagPage(QWidget):
    """Settings page for RAG configuration."""
    
    def __init__(
        self,
        settings_viewmodel: Optional[SettingsViewModel] = None,
        rag_service: Optional[RagService] = None,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the RAG page.
        
        Args:
            settings_viewmodel: The settings viewmodel.
            rag_service: The RAG service instance.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._settings_viewmodel = settings_viewmodel
        self._rag_service = rag_service
        self._setup_ui()
        self._connect_signals()
        self._load_settings()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Title
        title = QLabel("RAG Settings")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Description
        description = QLabel(
            "Configure Retrieval-Augmented Generation for local document search.\n"
            "Place PDF, text, and Markdown files in the knowledge base folder."
        )
        description.setStyleSheet("font-style: italic; margin-bottom: 10px;")
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # Knowledge base path
        path_section = QVBoxLayout()
        path_section.setSpacing(8)
        
        path_label = QLabel("Knowledge Base Folder:")
        path_label.setStyleSheet("font-weight: bold;")
        path_section.addWidget(path_label)
        
        path_row = QHBoxLayout()
        path_row.setSpacing(4)
        
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("~/Documents/Doc_RAG")
        self._path_edit.setFixedWidth(400)
        path_row.addWidget(self._path_edit)
        
        self._browse_btn = QPushButton("Browse...")
        self._browse_btn.setFixedWidth(100)
        path_row.addWidget(self._browse_btn)
        
        self._open_folder_btn = QPushButton("Open")
        self._open_folder_btn.setFixedWidth(80)
        self._open_folder_btn.setToolTip("Open knowledge base folder")
        path_row.addWidget(self._open_folder_btn)
        
        path_row.addStretch()
        
        path_section.addLayout(path_row)
        layout.addLayout(path_section)
        
        # Chunk settings
        chunk_section = QVBoxLayout()
        chunk_section.setSpacing(8)
        
        chunk_label = QLabel("Chunking Settings:")
        chunk_label.setStyleSheet("font-weight: bold;")
        chunk_section.addWidget(chunk_label)
        
        chunk_row = QHBoxLayout()
        chunk_row.setSpacing(16)
        
        # Chunk size
        size_layout = QHBoxLayout()
        size_layout.setSpacing(8)
        size_label = QLabel("Chunk Size:")
        size_layout.addWidget(size_label)
        self._chunk_size_spin = QSpinBox()
        self._chunk_size_spin.setRange(100, 10000)
        self._chunk_size_spin.setSingleStep(100)
        self._chunk_size_spin.setValue(1000)
        self._chunk_size_spin.setFixedWidth(100)
        size_layout.addWidget(self._chunk_size_spin)
        chunk_row.addLayout(size_layout)
        
        # Chunk overlap
        overlap_layout = QHBoxLayout()
        overlap_layout.setSpacing(8)
        overlap_label = QLabel("Overlap:")
        overlap_layout.addWidget(overlap_label)
        self._chunk_overlap_spin = QSpinBox()
        self._chunk_overlap_spin.setRange(0, 5000)
        self._chunk_overlap_spin.setSingleStep(50)
        self._chunk_overlap_spin.setValue(200)
        self._chunk_overlap_spin.setFixedWidth(100)
        overlap_layout.addWidget(self._chunk_overlap_spin)
        chunk_row.addLayout(overlap_layout)
        
        chunk_row.addStretch()
        chunk_section.addLayout(chunk_row)
        layout.addLayout(chunk_section)
        
        # Top-K setting
        topk_section = QHBoxLayout()
        topk_section.setSpacing(8)
        
        topk_label = QLabel("Top-K Results:")
        topk_label.setStyleSheet("font-weight: bold;")
        topk_section.addWidget(topk_label)
        
        self._top_k_spin = QSpinBox()
        self._top_k_spin.setRange(1, 20)
        self._top_k_spin.setValue(4)
        self._top_k_spin.setFixedWidth(80)
        topk_section.addWidget(self._top_k_spin)
        
        topk_section.addStretch()
        layout.addLayout(topk_section)
        
        # Embedding model
        embed_section = QVBoxLayout()
        embed_section.setSpacing(8)
        
        embed_label = QLabel("Embedding Model:")
        embed_label.setStyleSheet("font-weight: bold;")
        embed_section.addWidget(embed_label)
        
        self._embedding_model_combo = QComboBox()
        self._embedding_model_combo.setFixedWidth(400)
        embed_section.addWidget(self._embedding_model_combo)

        # Add model section
        add_model_section = QLabel("Add New Embedding Model")
        add_model_section.setStyleSheet("font-size: 12px; font-weight: bold; color: #89b4fa; margin-top: 10px;")
        embed_section.addWidget(add_model_section)

        add_model_row = QHBoxLayout()
        self._add_embedding_model_input = QLineEdit()
        self._add_embedding_model_input.setPlaceholderText("Enter model ID (e.g. provider/model-name)")
        self._add_embedding_model_input.setFixedWidth(400)
        
        self._add_embedding_model_btn = QPushButton("Add")
        self._add_embedding_model_btn.setFixedWidth(80)

        add_model_row.addWidget(self._add_embedding_model_input)
        add_model_row.addWidget(self._add_embedding_model_btn)
        add_model_row.addStretch()
        embed_section.addLayout(add_model_row)
        

        # Batch Size setting
        batch_layout = QHBoxLayout()
        batch_layout.setSpacing(8)
        batch_layout.setContentsMargins(0, 0, 0, 0)  # Add top margin to separate from embedding field
        batch_label = QLabel("Batch Size:")
        batch_layout.addWidget(batch_label, 0, Qt.AlignmentFlag.AlignVCenter)
        self._batch_size_spin = QSpinBox()
        self._batch_size_spin.setRange(1, 500)
        self._batch_size_spin.setValue(20)
        self._batch_size_spin.setToolTip("Number of chunks to process at once. Lower values prevent UI freezing.")
        self._batch_size_spin.setFixedWidth(80)
        batch_layout.addWidget(self._batch_size_spin, 0, Qt.AlignmentFlag.AlignVCenter)
        batch_layout.addStretch()
        embed_section.addLayout(batch_layout)
        
        layout.addLayout(embed_section)
        
        # Actions section
        actions_section = QVBoxLayout()
        actions_section.setSpacing(8)
        
        actions_label = QLabel("Index Actions:")
        actions_label.setStyleSheet("font-weight: bold;")
        actions_section.addWidget(actions_label)
        
        actions_row = QHBoxLayout()
        actions_row.setSpacing(12)
        
        self._reindex_btn = QPushButton("Reindex")
        self._reindex_btn.setStyleSheet(
            "background-color: #89b4fa; color: #1e1e2e; font-weight: bold; padding: 8px 16px;"
        )
        actions_row.addWidget(self._reindex_btn)
        
        self._clear_btn = QPushButton("Clear Index")
        self._clear_btn.setStyleSheet(
            "background-color: #f38ba8; color: #1e1e2e; padding: 8px 16px;"
        )
        actions_row.addWidget(self._clear_btn)
        
        actions_row.addStretch()
        actions_section.addLayout(actions_row)
        layout.addLayout(actions_section)
        
        # Status section
        status_section = QVBoxLayout()
        status_section.setSpacing(8)
        
        status_label = QLabel("Status:")
        status_label.setStyleSheet("font-weight: bold;")
        status_section.addWidget(status_label)
        
        self._status_label = QLabel("Not configured")
        self._status_label.setObjectName("ragStatusLabel")
        self._status_label.setProperty("state", "default")
        status_section.addWidget(self._status_label)
        
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        self._progress_bar.setTextVisible(True)
        status_section.addWidget(self._progress_bar)
        
        layout.addLayout(status_section)
        
        layout.addStretch()
    
    def _connect_signals(self) -> None:
        """Connect signals to slots."""
        self._browse_btn.clicked.connect(self._on_browse)
        self._open_folder_btn.clicked.connect(self._on_open_folder)
        self._reindex_btn.clicked.connect(self._on_reindex)
        self._clear_btn.clicked.connect(self._on_clear_index)
        
        # Settings changes
        self._path_edit.textChanged.connect(self._on_setting_changed)
        self._chunk_size_spin.valueChanged.connect(self._on_setting_changed)
        self._chunk_overlap_spin.valueChanged.connect(self._on_setting_changed)
        self._top_k_spin.valueChanged.connect(self._on_setting_changed)
        self._top_k_spin.valueChanged.connect(self._on_setting_changed)
        self._embedding_model_combo.currentTextChanged.connect(self._on_setting_changed)
        self._add_embedding_model_btn.clicked.connect(self._on_add_embedding_model)
        self._batch_size_spin.valueChanged.connect(self._on_setting_changed)
        
        # RAG service signals
        if self._rag_service:
            self._rag_service.status_changed.connect(self._on_status_changed)
            self._rag_service.index_ready.connect(self._on_index_ready)
            self._rag_service.indexing_started.connect(self._on_indexing_started)
            self._rag_service.indexing_progress.connect(self._on_indexing_progress)
            self._rag_service.indexing_completed.connect(self._on_indexing_completed)
            self._rag_service.indexing_error.connect(self._on_indexing_error)
    
    def _load_settings(self) -> None:
        """Load settings from viewmodel."""
        if not self._settings_viewmodel:
            return
        
        self._path_edit.setText(self._settings_viewmodel.rag_knowledge_base_path)
        self._chunk_size_spin.setValue(self._settings_viewmodel.rag_chunk_size)
        self._chunk_overlap_spin.setValue(self._settings_viewmodel.rag_chunk_overlap)
        self._top_k_spin.setValue(self._settings_viewmodel.rag_top_k)
        self._top_k_spin.setValue(self._settings_viewmodel.rag_top_k)
        
        self._refresh_embedding_model_combo()
        self._batch_size_spin.setValue(self._settings_viewmodel.rag_embedding_batch_size)
        
        # Update status
        if self._rag_service and self._rag_service.is_ready:
            self._status_label.setText("Index ready")
            self._update_status_state("ready")
        else:
            self._status_label.setText("Not indexed")
            self._update_status_state("default")
    
    @Slot()
    def _on_setting_changed(self) -> None:
        """Handle setting changes."""
        if not self._settings_viewmodel:
            return
        
        self._settings_viewmodel.rag_knowledge_base_path = self._path_edit.text()
        self._settings_viewmodel.rag_chunk_size = self._chunk_size_spin.value()
        self._settings_viewmodel.rag_chunk_overlap = self._chunk_overlap_spin.value()
        self._settings_viewmodel.rag_top_k = self._top_k_spin.value()
        self._settings_viewmodel.rag_top_k = self._top_k_spin.value()
        self._settings_viewmodel.rag_embedding_model = self._embedding_model_combo.currentText() or "openai/text-embedding-3-small"
        self._settings_viewmodel.rag_embedding_batch_size = self._batch_size_spin.value()
    
    @Slot()
    def _on_browse(self) -> None:
        """Handle browse button click."""
        current = self._path_edit.text() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(
            self, "Select Knowledge Base Folder", current
        )
        if folder:
            self._path_edit.setText(folder)
    
    @Slot()
    def _on_open_folder(self) -> None:
        """Open the knowledge base folder."""
        path = Path(self._path_edit.text() or str(Path.home() / "Documents" / "Doc_RAG"))
        
        # Ensure folder exists
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        
        # Open in file manager
        if path.exists():
            try:
                if os.name == "nt":  # Windows
                    os.startfile(str(path))
                elif os.name == "posix":
                    subprocess.run(["xdg-open", str(path)], check=False)
            except Exception:
                pass
    
    @Slot()
    def _on_reindex(self) -> None:
        """Handle reindex button click."""
        if not self._rag_service:
            return
        
        # Get API key from settings
        api_key = None
        if self._settings_viewmodel:
            api_key = self._settings_viewmodel.api_key
        
        # Configure service with current settings
        self._rag_service.configure(
            knowledge_base_path=self._path_edit.text(),
            chunk_size=self._chunk_size_spin.value(),
            chunk_overlap=self._chunk_overlap_spin.value(),
            top_k=self._top_k_spin.value(),
            embedding_model=self._embedding_model_combo.currentText() or "openai/text-embedding-3-small",
            embedding_batch_size=self._batch_size_spin.value(),
            api_key=api_key,
        )
        
        # Ensure folder exists
        self._rag_service.ensure_knowledge_base_path()
        
        # Start reindex
        self._rag_service.reindex()
    
    @Slot()
    def _on_clear_index(self) -> None:
        """Handle clear index button click."""
        if self._rag_service:
            self._rag_service.clear_index()
            self._status_label.setText("Index cleared")
            self._update_status_state("default")
    
    @Slot(str)
    def _on_status_changed(self, status: str) -> None:
        """Handle status change."""
        self._status_label.setText(status)
    
    @Slot(bool)
    def _on_index_ready(self, ready: bool) -> None:
        """Handle index ready signal."""
        if ready:
            self._update_status_state("ready")
        else:
            self._update_status_state("default")
    
    @Slot()
    def _on_indexing_started(self) -> None:
        """Handle indexing started."""
        self._reindex_btn.setEnabled(False)
        self._clear_btn.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(0)
    
    @Slot(int, int)
    def _on_indexing_progress(self, current: int, total: int) -> None:
        """Handle indexing progress."""
        if total > 0:
            self._progress_bar.setMaximum(total)
            self._progress_bar.setValue(current)
    
    @Slot(bool, int)
    def _on_indexing_completed(self, success: bool, num_chunks: int) -> None:
        """Handle indexing completed."""
        self._reindex_btn.setEnabled(True)
        self._clear_btn.setEnabled(True)
        self._progress_bar.setVisible(False)
        
        if success:
            self._status_label.setText(f"Indexed {num_chunks} chunks")
            self._update_status_state("ready")
    
    @Slot(str)
    def _on_indexing_error(self, error: str) -> None:
        """Handle indexing error."""
        self._reindex_btn.setEnabled(True)
        self._clear_btn.setEnabled(True)
        self._progress_bar.setVisible(False)
        self._status_label.setText(f"Error: {error}")
        self._update_status_state("error")
    
    def set_rag_service(self, rag_service: RagService) -> None:
        """Set the RAG service after initialization.
        
        Args:
            rag_service: The RAG service instance.
        """
        self._rag_service = rag_service
        
        # Reconnect signals
        self._rag_service.status_changed.connect(self._on_status_changed)
        self._rag_service.index_ready.connect(self._on_index_ready)
        self._rag_service.indexing_started.connect(self._on_indexing_started)
        self._rag_service.indexing_progress.connect(self._on_indexing_progress)
        self._rag_service.indexing_completed.connect(self._on_indexing_completed)
        self._rag_service.indexing_error.connect(self._on_indexing_error)
        
        # Update status
        if self._rag_service.is_ready:
            self._on_index_ready(True)
            
    def _update_status_state(self, state: str) -> None:
        """Update the status label state property and refresh style."""
        self._status_label.setProperty("state", state)
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

    def _refresh_embedding_model_combo(self) -> None:
        """Refresh the embedding model combo."""
        if not self._settings_viewmodel:
            return
            
        self._embedding_model_combo.clear()
        for model in self._settings_viewmodel.rag_embedding_models:
            self._embedding_model_combo.addItem(model)
        
        # Set current default
        index = self._embedding_model_combo.findText(self._settings_viewmodel.rag_embedding_model)
        if index >= 0:
            self._embedding_model_combo.setCurrentIndex(index)

    def _on_add_embedding_model(self) -> None:
        """Handle add embedding model button."""
        if not self._settings_viewmodel:
            return
            
        model = self._add_embedding_model_input.text().strip()
        if model:
            self._settings_viewmodel.add_embedding_model(model)
            self._add_embedding_model_input.clear()
            self._refresh_embedding_model_combo()
