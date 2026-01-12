"""Application entry point."""

import logging
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .persistence import (
    Database,
    MessageRepository,
    ChatRepository,
    WorkspaceRepository,
    AgentMemoryRepository,
    WorkspaceMemoryRepository,
    SettingsRepository,
    AttachmentRepository,
)
from .core.agents import AgentRepository
from .infrastructure import LangChainService, MemoryAggregationService, RagService, ScreenCaptureService
from .infrastructure.capture_cleanup_service import CaptureCleanupService
from .infrastructure.logging_config import configure_logging
from .viewmodels import (
    ChatViewModel,
    WorkspaceViewModel,
    WorkspaceMemoryViewModel,
    MainViewModel,
    SettingsViewModel,
)
from .views import MainWindow


project_root = Path(__file__).resolve().parents[1]

def main() -> int:
    """Main entry point for the application.
    
    Returns:
        Exit code.
    """
    configure_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Attractor Desk")

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Attractor Desk")
    app.setOrganizationName("AttractorDesk")
    
    icon_path = project_root / "attractor_desk" / "assets" / "icons" / "attractor_icon.ico"
    app.setWindowIcon(QIcon(str(icon_path)))
    
    # Initialize database
    database = Database()
    
    # Initialize repositories
    message_repo = MessageRepository(database)
    chat_repo = ChatRepository(database)
    workspace_repo = WorkspaceRepository(database)
    agent_memory_repo = AgentMemoryRepository(database)
    workspace_memory_repo = WorkspaceMemoryRepository(database)
    settings_repo = SettingsRepository(database)
    attachment_repo = AttachmentRepository(database)
    
    # Initialize agent repository with hot reload callback
    agents_dir = project_root / "agents"
    agent_repo = AgentRepository(agents_dir=agents_dir)
    
    # Initialize settings viewmodel
    settings_viewmodel = SettingsViewModel(
        settings_db=database,
    )

    # Initialize services
    langchain_service = LangChainService()
    memory_aggregation_service = MemoryAggregationService(
        workspace_memory_repo=workspace_memory_repo,
        message_repo=message_repo,
        chat_repo=chat_repo,
        langchain_service=langchain_service,
    )
    
    # Initialize RAG service with settings
    rag_service = RagService()
    rag_service.configure(
        knowledge_base_path=settings_viewmodel.rag_knowledge_base_path,
        chunk_size=settings_viewmodel.rag_chunk_size,
        chunk_overlap=settings_viewmodel.rag_chunk_overlap,
        top_k=settings_viewmodel.rag_top_k,
        embedding_model=settings_viewmodel.rag_embedding_model,
        api_key=settings_viewmodel.api_key,
    )
    
    # Ensure knowledge base folder exists on startup
    rag_service.ensure_knowledge_base_path()
    
    # Initialize screen capture services
    screen_capture_service = ScreenCaptureService()
    capture_cleanup_service = CaptureCleanupService()
    
    # Ensure capture folder exists
    capture_cleanup_service.ensure_capture_folder(settings_viewmodel.capture_storage_path)
    
    # Run cleanup if needed (weekly)
    capture_cleanup_service.run_cleanup_if_needed(settings_viewmodel, attachment_repo)
    
    # Initialize viewmodels
    chat_viewmodel = ChatViewModel(
        message_repository=message_repo,
        chat_repository=chat_repo,
        agent_repository=agent_repo,
        agent_memory_repository=agent_memory_repo,
        workspace_memory_repository=workspace_memory_repo,
        langchain_service=langchain_service,
        settings_repository=settings_repo,
        memory_aggregation_service=memory_aggregation_service,
        rag_service=rag_service,
        attachment_repository=attachment_repo,
        settings_viewmodel=settings_viewmodel,
    )
    
    # Wire agent reload callback (calls _refresh_agents to avoid recursion)
    agent_repo._on_agents_changed = lambda: chat_viewmodel._refresh_agents()
    
    workspace_viewmodel = WorkspaceViewModel(
        workspace_repository=workspace_repo,
        chat_repository=chat_repo,
        message_repository=message_repo,
    )

    workspace_memory_viewmodel = WorkspaceMemoryViewModel(
        memory_repository=workspace_memory_repo,
        aggregation_service=memory_aggregation_service,
    )
    
    main_viewmodel = MainViewModel(
        chat_viewmodel=chat_viewmodel,
        workspace_viewmodel=workspace_viewmodel,
        workspace_memory_viewmodel=workspace_memory_viewmodel,
    )
    
    # Start agent file watching for hot reload
    agent_repo.start_watching()
    
    # Create and show main window
    window = MainWindow(
        viewmodel=main_viewmodel,
        settings_viewmodel=settings_viewmodel,
        rag_service=rag_service,
        screen_capture_service=screen_capture_service,
    )
    window.show()
    
    # Run event loop
    exit_code = app.exec()
    
    # Cleanup
    rag_service.shutdown()  # Stop RAG workers before closing
    screen_capture_service.cleanup()  # Clean up mss resources
    agent_repo.stop_watching()
    database.close()
    
    logger.info("Exited Attractor Desk with code %s", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
