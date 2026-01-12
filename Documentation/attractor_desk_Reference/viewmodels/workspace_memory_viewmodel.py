"""ViewModel for managing workspace memories."""

from typing import List, Optional

from PySide6.QtCore import QObject, Signal, Property, Slot

from ..core.models import WorkspaceMemory, MemorySourceType
from ..persistence import WorkspaceMemoryRepository
from ..infrastructure import MemoryAggregationService


class WorkspaceMemoryViewModel(QObject):
    """ViewModel for workspace memory management."""

    memories_changed = Signal()
    current_workspace_changed = Signal()
    error_occurred = Signal(str)
    summarization_started = Signal(str, str)
    summarization_completed = Signal(str, str)
    summarization_error = Signal(str)

    def __init__(
        self,
        memory_repository: WorkspaceMemoryRepository,
        aggregation_service: Optional[MemoryAggregationService] = None,
        parent: Optional[QObject] = None,
    ):
        """Initialize the WorkspaceMemoryViewModel.

        Args:
            memory_repository: Repository for workspace memories.
            aggregation_service: Optional aggregation service for refresh hooks.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self._memory_repository = memory_repository
        self._aggregation_service = aggregation_service
        self._memories: List[WorkspaceMemory] = []
        self._current_workspace_id: Optional[str] = None
        self._search_query = ""
        self._source_filter: Optional[MemorySourceType] = None

        if self._aggregation_service is not None:
            self._aggregation_service.summarization_started.connect(
                self.summarization_started.emit
            )
            self._aggregation_service.summarization_completed.connect(
                self._on_summarization_completed
            )
            self._aggregation_service.summarization_completed.connect(
                self.summarization_completed.emit
            )
            self._aggregation_service.summarization_error.connect(
                self.summarization_error.emit
            )
            self._aggregation_service.summarization_error.connect(
                self.error_occurred.emit
            )

    @Property(list, notify=memories_changed)
    def memories(self) -> List[WorkspaceMemory]:
        """Get the current workspace memories."""
        return self._memories

    @Property(str, notify=current_workspace_changed)
    def current_workspace_id(self) -> Optional[str]:
        """Get the current workspace ID."""
        return self._current_workspace_id

    @Slot(str)
    def load_workspace(self, workspace_id: str) -> None:
        """Load memories for a workspace."""
        self._current_workspace_id = workspace_id
        self._search_query = ""
        self._source_filter = None
        self.current_workspace_changed.emit()
        self._refresh()

    @Slot(str, int)
    def add_memory(self, content: str, priority: int = 0) -> None:
        """Add a new user memory to the current workspace."""
        if not self._current_workspace_id:
            self.error_occurred.emit("No workspace selected.")
            return
        if not content.strip():
            return
        memory = WorkspaceMemory.create(
            workspace_id=self._current_workspace_id,
            content=content.strip(),
            source_type=MemorySourceType.USER_ADDED,
            priority=priority,
        )
        self._memory_repository.add(memory)
        self._refresh()

    @Slot(str, str, int)
    def update_memory(self, memory_id: str, content: str, priority: int) -> None:
        """Update an existing memory."""
        memory = self._memory_repository.get_by_id(memory_id)
        if memory is None:
            self.error_occurred.emit("Memory not found.")
            return
        memory.content = content.strip()
        memory.priority = priority
        self._memory_repository.update(memory)
        self._refresh()

    @Slot(str)
    def delete_memory(self, memory_id: str) -> None:
        """Delete a memory."""
        self._memory_repository.delete(memory_id)
        self._refresh()

    @Slot(str)
    def search(self, query: str) -> None:
        """Search memories by content."""
        self._search_query = query.strip()
        self._refresh()

    @Slot(str)
    def filter_by_source(self, source_type: Optional[str]) -> None:
        """Filter memories by source type."""
        if source_type:
            try:
                self._source_filter = MemorySourceType(source_type)
            except ValueError:
                self._source_filter = None
        else:
            self._source_filter = None
        self._refresh()

    def _refresh(self) -> None:
        """Refresh memory list based on filters."""
        if not self._current_workspace_id:
            self._memories = []
            self.memories_changed.emit()
            return

        if self._search_query:
            memories = self._memory_repository.search(
                self._current_workspace_id, self._search_query
            )
        else:
            memories = self._memory_repository.get_by_workspace(
                self._current_workspace_id, self._source_filter
            )

        if self._source_filter and self._search_query:
            memories = [
                memory
                for memory in memories
                if memory.source_type == self._source_filter
            ]

        self._memories = memories
        self.memories_changed.emit()

    def _on_summarization_completed(self, workspace_id: str, summary: str) -> None:
        """Refresh memories when summarization completes."""
        if workspace_id == self._current_workspace_id:
            self._refresh()
