"""RAGConfigurationSettings - RAG algorithm parameters and feature flags."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal

from core.constants import DEFAULT_EMBEDDING_MODEL
from core.persistence import Database, SettingsRepository


class RAGConfigurationSettings(QObject):
    """Manages RAG configuration parameters (no operations, pure settings)."""

    settings_changed = Signal()

    KEY_RAG_ENABLED = "rag.enabled"
    KEY_RAG_SCOPE = "rag.scope"
    KEY_RAG_CHUNK_SIZE = "rag.chunk_size_chars"
    KEY_RAG_CHUNK_OVERLAP = "rag.chunk_overlap_chars"
    KEY_RAG_K_LEX = "rag.k_lex"
    KEY_RAG_K_VEC = "rag.k_vec"
    KEY_RAG_RRF_K = "rag.rrf_k"
    KEY_RAG_MAX_CANDIDATES = "rag.max_candidates"
    KEY_RAG_EMBEDDING_MODEL = "rag.embedding_model"
    KEY_RAG_ENABLE_QUERY_REWRITE = "rag.enable_query_rewrite"
    KEY_RAG_ENABLE_LLM_RERANK = "rag.enable_llm_rerank"
    KEY_RAG_INDEX_TEXT = "rag.index_text_artifacts"
    KEY_RAG_GLOBAL_FOLDER = "rag.global_folder"
    KEY_RAG_GLOBAL_MONITORING = "rag.global_monitoring_enabled"
    KEY_RAG_CHATPDF_RETENTION_DAYS = "rag.chatpdf_retention_days"

    def __init__(
        self,
        database: Optional[Database] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._db = database or Database()
        self._repo = SettingsRepository(self._db)

        # Internal state
        self._rag_enabled: bool = False
        self._rag_scope: str = "global"
        self._rag_chunk_size_chars: int = 1200
        self._rag_chunk_overlap_chars: int = 150
        self._rag_k_lex: int = 8
        self._rag_k_vec: int = 8
        self._rag_rrf_k: int = 60
        self._rag_max_candidates: int = 12
        self._rag_embedding_model: str = DEFAULT_EMBEDDING_MODEL
        self._rag_enable_query_rewrite: bool = False
        self._rag_enable_llm_rerank: bool = False
        self._rag_index_text_artifacts: bool = False
        self._rag_global_folder: str = str(Path.home() / "Documents" / "AttractorDeskRAG")
        self._rag_global_monitoring_enabled: bool = False
        self._rag_chatpdf_retention_days: int = 7

    @property
    def rag_enabled(self) -> bool:
        """Get RAG enabled state."""
        return self._rag_enabled

    @rag_enabled.setter
    def rag_enabled(self, value: bool) -> None:
        """Set RAG enabled state."""
        value = bool(value)
        if self._rag_enabled != value:
            self._rag_enabled = value
            self.settings_changed.emit()

    @property
    def rag_scope(self) -> str:
        """Get RAG scope (session/workspace/global)."""
        return self._rag_scope

    @rag_scope.setter
    def rag_scope(self, value: str) -> None:
        """Set RAG scope."""
        value = value if value in ("session", "workspace", "global") else "global"
        if self._rag_scope != value:
            self._rag_scope = value
            self.settings_changed.emit()

    @property
    def rag_chunk_size_chars(self) -> int:
        """Get chunk size in characters."""
        return self._rag_chunk_size_chars

    @rag_chunk_size_chars.setter
    def rag_chunk_size_chars(self, value: int) -> None:
        """Set chunk size, clamped to 200-5000. Adjusts overlap if needed."""
        value = max(200, min(5000, int(value)))
        if self._rag_chunk_size_chars != value:
            self._rag_chunk_size_chars = value
            # Ensure overlap is less than chunk size
            if self._rag_chunk_overlap_chars >= value:
                self._rag_chunk_overlap_chars = max(0, value - 1)
            self.settings_changed.emit()

    @property
    def rag_chunk_overlap_chars(self) -> int:
        """Get chunk overlap in characters."""
        return self._rag_chunk_overlap_chars

    @rag_chunk_overlap_chars.setter
    def rag_chunk_overlap_chars(self, value: int) -> None:
        """Set chunk overlap, clamped to 0-1000 and less than chunk size."""
        value = max(0, min(1000, int(value)))
        if value >= self._rag_chunk_size_chars:
            value = max(0, self._rag_chunk_size_chars - 1)
        if self._rag_chunk_overlap_chars != value:
            self._rag_chunk_overlap_chars = value
            self.settings_changed.emit()

    @property
    def rag_k_lex(self) -> int:
        """Get number of lexical search results."""
        return self._rag_k_lex

    @rag_k_lex.setter
    def rag_k_lex(self, value: int) -> None:
        """Set number of lexical search results, clamped to 1-50."""
        value = max(1, min(50, int(value)))
        if self._rag_k_lex != value:
            self._rag_k_lex = value
            self.settings_changed.emit()

    @property
    def rag_k_vec(self) -> int:
        """Get number of vector search results."""
        return self._rag_k_vec

    @rag_k_vec.setter
    def rag_k_vec(self, value: int) -> None:
        """Set number of vector search results, clamped to 0-50."""
        value = max(0, min(50, int(value)))
        if self._rag_k_vec != value:
            self._rag_k_vec = value
            self.settings_changed.emit()

    @property
    def rag_rrf_k(self) -> int:
        """Get RRF (Reciprocal Rank Fusion) constant."""
        return self._rag_rrf_k

    @rag_rrf_k.setter
    def rag_rrf_k(self, value: int) -> None:
        """Set RRF constant, clamped to 10-200."""
        value = max(10, min(200, int(value)))
        if self._rag_rrf_k != value:
            self._rag_rrf_k = value
            self.settings_changed.emit()

    @property
    def rag_max_candidates(self) -> int:
        """Get maximum candidate results before reranking."""
        return self._rag_max_candidates

    @rag_max_candidates.setter
    def rag_max_candidates(self, value: int) -> None:
        """Set maximum candidates, clamped to 1-50."""
        value = max(1, min(50, int(value)))
        if self._rag_max_candidates != value:
            self._rag_max_candidates = value
            self.settings_changed.emit()

    @property
    def rag_embedding_model(self) -> str:
        """Get embedding model identifier."""
        return self._rag_embedding_model

    @rag_embedding_model.setter
    def rag_embedding_model(self, value: str) -> None:
        """Set embedding model identifier."""
        value = (value or "").strip()
        if self._rag_embedding_model != value:
            self._rag_embedding_model = value
            self.settings_changed.emit()

    @property
    def rag_enable_query_rewrite(self) -> bool:
        """Get query rewrite enabled state."""
        return self._rag_enable_query_rewrite

    @rag_enable_query_rewrite.setter
    def rag_enable_query_rewrite(self, value: bool) -> None:
        """Set query rewrite enabled state."""
        value = bool(value)
        if self._rag_enable_query_rewrite != value:
            self._rag_enable_query_rewrite = value
            self.settings_changed.emit()

    @property
    def rag_enable_llm_rerank(self) -> bool:
        """Get LLM rerank enabled state."""
        return self._rag_enable_llm_rerank

    @rag_enable_llm_rerank.setter
    def rag_enable_llm_rerank(self, value: bool) -> None:
        """Set LLM rerank enabled state."""
        value = bool(value)
        if self._rag_enable_llm_rerank != value:
            self._rag_enable_llm_rerank = value
            self.settings_changed.emit()

    @property
    def rag_index_text_artifacts(self) -> bool:
        """Get text artifacts indexing enabled state."""
        return self._rag_index_text_artifacts

    @rag_index_text_artifacts.setter
    def rag_index_text_artifacts(self, value: bool) -> None:
        """Set text artifacts indexing enabled state."""
        value = bool(value)
        if self._rag_index_text_artifacts != value:
            self._rag_index_text_artifacts = value
            self.settings_changed.emit()

    @property
    def rag_global_folder(self) -> str:
        """Get global RAG folder path."""
        return self._rag_global_folder

    @rag_global_folder.setter
    def rag_global_folder(self, value: str) -> None:
        """Set global RAG folder path (NO side effects - monitoring handled externally)."""
        value = (value or "").strip()
        if self._rag_global_folder != value:
            self._rag_global_folder = value
            self.settings_changed.emit()
            # NOTE: Monitoring restart moved to GlobalRAGOrchestrator

    @property
    def rag_global_monitoring_enabled(self) -> bool:
        """Get global folder monitoring enabled state."""
        return self._rag_global_monitoring_enabled

    @rag_global_monitoring_enabled.setter
    def rag_global_monitoring_enabled(self, value: bool) -> None:
        """Set global folder monitoring enabled state (NO side effects - handled externally)."""
        value = bool(value)
        if self._rag_global_monitoring_enabled != value:
            self._rag_global_monitoring_enabled = value
            self.settings_changed.emit()
            # NOTE: Monitoring start/stop moved to GlobalRAGOrchestrator

    @property
    def rag_chatpdf_retention_days(self) -> int:
        """Get ChatPDF retention days."""
        return self._rag_chatpdf_retention_days

    @rag_chatpdf_retention_days.setter
    def rag_chatpdf_retention_days(self, value: int) -> None:
        """Set ChatPDF retention days, clamped to 1-90."""
        value = max(1, min(90, int(value)))
        if self._rag_chatpdf_retention_days != value:
            self._rag_chatpdf_retention_days = value
            self.settings_changed.emit()

    def load(self) -> None:
        """Load RAG configuration from database."""
        self._rag_enabled = self._repo.get_bool(self.KEY_RAG_ENABLED, False)
        self._rag_scope = self._repo.get_value(self.KEY_RAG_SCOPE, "global")
        self._rag_chunk_size_chars = self._repo.get_int(self.KEY_RAG_CHUNK_SIZE, 1200)
        self._rag_chunk_overlap_chars = self._repo.get_int(
            self.KEY_RAG_CHUNK_OVERLAP, 150
        )

        # Ensure overlap < chunk size
        if self._rag_chunk_overlap_chars >= self._rag_chunk_size_chars:
            self._rag_chunk_overlap_chars = max(0, self._rag_chunk_size_chars - 1)

        self._rag_k_lex = self._repo.get_int(self.KEY_RAG_K_LEX, 8)
        self._rag_k_vec = self._repo.get_int(self.KEY_RAG_K_VEC, 8)
        self._rag_rrf_k = self._repo.get_int(self.KEY_RAG_RRF_K, 60)
        self._rag_max_candidates = self._repo.get_int(self.KEY_RAG_MAX_CANDIDATES, 12)
        self._rag_embedding_model = self._repo.get_value(
            self.KEY_RAG_EMBEDDING_MODEL, DEFAULT_EMBEDDING_MODEL
        )
        self._rag_enable_query_rewrite = self._repo.get_bool(
            self.KEY_RAG_ENABLE_QUERY_REWRITE, False
        )
        self._rag_enable_llm_rerank = self._repo.get_bool(
            self.KEY_RAG_ENABLE_LLM_RERANK, False
        )
        self._rag_index_text_artifacts = self._repo.get_bool(
            self.KEY_RAG_INDEX_TEXT, False
        )
        self._rag_global_folder = self._repo.get_value(
            self.KEY_RAG_GLOBAL_FOLDER,
            str(Path.home() / "Documents" / "AttractorDeskRAG"),
        )
        self._rag_global_monitoring_enabled = self._repo.get_bool(
            self.KEY_RAG_GLOBAL_MONITORING, False
        )
        self._rag_chatpdf_retention_days = self._repo.get_int(
            self.KEY_RAG_CHATPDF_RETENTION_DAYS, 7
        )

    def save(self) -> None:
        """Save RAG configuration to database."""
        self._repo.set(
            self.KEY_RAG_ENABLED, str(self._rag_enabled).lower(), "rag"
        )
        self._repo.set(self.KEY_RAG_SCOPE, self._rag_scope, "rag")
        self._repo.set(
            self.KEY_RAG_CHUNK_SIZE, str(self._rag_chunk_size_chars), "rag"
        )
        self._repo.set(
            self.KEY_RAG_CHUNK_OVERLAP, str(self._rag_chunk_overlap_chars), "rag"
        )
        self._repo.set(self.KEY_RAG_K_LEX, str(self._rag_k_lex), "rag")
        self._repo.set(self.KEY_RAG_K_VEC, str(self._rag_k_vec), "rag")
        self._repo.set(self.KEY_RAG_RRF_K, str(self._rag_rrf_k), "rag")
        self._repo.set(
            self.KEY_RAG_MAX_CANDIDATES, str(self._rag_max_candidates), "rag"
        )
        self._repo.set(
            self.KEY_RAG_EMBEDDING_MODEL, self._rag_embedding_model, "rag"
        )
        self._repo.set(
            self.KEY_RAG_ENABLE_QUERY_REWRITE,
            str(self._rag_enable_query_rewrite).lower(),
            "rag",
        )
        self._repo.set(
            self.KEY_RAG_ENABLE_LLM_RERANK,
            str(self._rag_enable_llm_rerank).lower(),
            "rag",
        )
        self._repo.set(
            self.KEY_RAG_INDEX_TEXT,
            str(self._rag_index_text_artifacts).lower(),
            "rag",
        )
        self._repo.set(self.KEY_RAG_GLOBAL_FOLDER, self._rag_global_folder, "rag")
        self._repo.set(
            self.KEY_RAG_GLOBAL_MONITORING,
            str(self._rag_global_monitoring_enabled).lower(),
            "rag",
        )
        self._repo.set(
            self.KEY_RAG_CHATPDF_RETENTION_DAYS,
            str(self._rag_chatpdf_retention_days),
            "rag",
        )

    def snapshot(self) -> dict[str, object]:
        """Create snapshot of current state for revert functionality."""
        return {
            "rag_enabled": self._rag_enabled,
            "rag_scope": self._rag_scope,
            "rag_chunk_size_chars": self._rag_chunk_size_chars,
            "rag_chunk_overlap_chars": self._rag_chunk_overlap_chars,
            "rag_k_lex": self._rag_k_lex,
            "rag_k_vec": self._rag_k_vec,
            "rag_rrf_k": self._rag_rrf_k,
            "rag_max_candidates": self._rag_max_candidates,
            "rag_embedding_model": self._rag_embedding_model,
            "rag_enable_query_rewrite": self._rag_enable_query_rewrite,
            "rag_enable_llm_rerank": self._rag_enable_llm_rerank,
            "rag_index_text_artifacts": self._rag_index_text_artifacts,
            "rag_global_folder": self._rag_global_folder,
            "rag_global_monitoring_enabled": self._rag_global_monitoring_enabled,
            "rag_chatpdf_retention_days": self._rag_chatpdf_retention_days,
        }

    def restore_snapshot(self, snapshot: dict[str, object]) -> None:
        """Restore state from snapshot, emitting signals for changes."""
        self._rag_enabled = bool(snapshot.get("rag_enabled", False))
        self._rag_scope = snapshot.get("rag_scope", "global") or "global"
        self._rag_chunk_size_chars = int(snapshot.get("rag_chunk_size_chars", 1200))
        self._rag_chunk_overlap_chars = int(snapshot.get("rag_chunk_overlap_chars", 150))
        self._rag_k_lex = int(snapshot.get("rag_k_lex", 8))
        self._rag_k_vec = int(snapshot.get("rag_k_vec", 8))
        self._rag_rrf_k = int(snapshot.get("rag_rrf_k", 60))
        self._rag_max_candidates = int(snapshot.get("rag_max_candidates", 12))
        self._rag_embedding_model = snapshot.get(
            "rag_embedding_model", DEFAULT_EMBEDDING_MODEL
        )
        self._rag_enable_query_rewrite = bool(
            snapshot.get("rag_enable_query_rewrite", False)
        )
        self._rag_enable_llm_rerank = bool(snapshot.get("rag_enable_llm_rerank", False))
        self._rag_index_text_artifacts = bool(
            snapshot.get("rag_index_text_artifacts", False)
        )
        self._rag_global_folder = snapshot.get(
            "rag_global_folder",
            str(Path.home() / "Documents" / "AttractorDeskRAG"),
        )
        self._rag_global_monitoring_enabled = bool(
            snapshot.get("rag_global_monitoring_enabled", False)
        )
        self._rag_chatpdf_retention_days = int(
            snapshot.get("rag_chatpdf_retention_days", 7)
        )
        self.settings_changed.emit()
