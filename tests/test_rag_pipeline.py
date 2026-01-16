"""Integration and service tests for the RAG pipeline."""

from pathlib import Path

from langchain_core.messages import HumanMessage

from core.graphs.rag.graph import graph as rag_graph
from core.graphs.rag import nodes as rag_nodes
from core.models import Session, Workspace
from core.persistence import Database, SessionRepository, WorkspaceRepository
from core.persistence.rag_repository import RagChunkInput, RagRepository
from core.services.docling_service import PdfConversionResult
from core.services.global_rag_service import GlobalRagIndexRequest, _GlobalIndexWorker
from core.services.local_rag_service import LocalRagIndexRequest, _LocalIndexWorker


def test_global_rag_index_worker_success(tmp_path, monkeypatch) -> None:
    db = Database(tmp_path / "rag.db")
    repository = RagRepository(db)

    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")

    def fake_convert(path: str) -> PdfConversionResult:
        return PdfConversionResult(
            success=True,
            markdown="Global PDF content",
            source_filename=Path(path).stem,
        )

    monkeypatch.setattr(
        "core.services.global_rag_service.convert_pdf_to_markdown",
        fake_convert,
    )

    request = GlobalRagIndexRequest(
        workspace_id="GLOBAL",
        pdf_paths=[str(pdf_path)],
        embeddings_enabled=False,
    )
    worker = _GlobalIndexWorker(repository, request)
    result = worker._run_index()

    assert result.indexed == 1
    entries = repository.list_registry_entries()
    assert entries
    assert entries[0].status == "indexed"

    hits = repository.search_lexical(
        query="Global",
        scope="global",
        workspace_id=None,
        session_id=None,
        limit=5,
    )
    assert hits


def test_global_rag_index_worker_missing_file(tmp_path) -> None:
    db = Database(tmp_path / "rag.db")
    repository = RagRepository(db)

    request = GlobalRagIndexRequest(
        workspace_id="GLOBAL",
        pdf_paths=[str(tmp_path / "missing.pdf")],
        embeddings_enabled=False,
    )
    worker = _GlobalIndexWorker(repository, request)
    result = worker._run_index()

    assert result.failed == 1
    entries = repository.list_registry_entries()
    assert entries[0].status == "error"


def test_local_rag_index_worker_success(tmp_path, monkeypatch) -> None:
    db = Database(tmp_path / "rag.db")
    workspace_repo = WorkspaceRepository(db)
    session_repo = SessionRepository(db)
    workspace = Workspace.create("ChatPDF")
    workspace_repo.create(workspace)
    session = Session.create(workspace.id, title="Session")
    session_repo.create(session)

    repository = RagRepository(db)

    source_pdf = tmp_path / "session.pdf"
    source_pdf.write_bytes(b"%PDF-1.4 local")

    def fake_convert(path: str) -> PdfConversionResult:
        return PdfConversionResult(
            success=True,
            markdown="Local PDF content",
            source_filename=Path(path).stem,
        )

    monkeypatch.setattr(
        "core.services.local_rag_service.convert_pdf_to_markdown",
        fake_convert,
    )
    monkeypatch.setattr(
        "core.services.local_rag_service.CHATPDF_STORAGE_DIR",
        tmp_path,
    )

    request = LocalRagIndexRequest(
        workspace_id=workspace.id,
        session_id=session.id,
        pdf_path=str(source_pdf),
        embeddings_enabled=False,
    )
    worker = _LocalIndexWorker(repository, request)
    result = worker._run_index()

    assert result.success is True
    assert result.document_id
    assert result.saved_path
    assert Path(result.saved_path).exists()


def test_local_rag_index_worker_missing_file(tmp_path) -> None:
    db = Database(tmp_path / "rag.db")
    repository = RagRepository(db)
    request = LocalRagIndexRequest(
        workspace_id="workspace",
        session_id="session",
        pdf_path=str(tmp_path / "missing.pdf"),
        embeddings_enabled=False,
    )
    worker = _LocalIndexWorker(repository, request)
    result = worker._run_index()

    assert result.success is False
    assert result.error_message == "File not found"


def test_rag_graph_global_flow(tmp_path, monkeypatch) -> None:
    db = Database(tmp_path / "rag.db")
    repository = RagRepository(db)
    document = repository.create_document(
        workspace_id="GLOBAL",
        source_type="pdf",
        source_name="GlobalDoc",
        content_hash="hash",
    )
    repository.replace_document_chunks(
        document.id,
        [
            RagChunkInput(
                id="chunk-1",
                chunk_index=0,
                content="Global knowledge snippet",
                section_title="Global",
            )
        ],
        source_name="GlobalDoc",
    )

    monkeypatch.setattr(rag_nodes, "Database", lambda: db)

    state = {
        "messages": [HumanMessage(content="Global")],
        "conversation_mode": "normal",
    }
    config = {
        "configurable": {
            "rag_enabled": True,
            "rag_scope": "global",
            "rag_k_lex": 5,
            "rag_k_vec": 0,
        }
    }
    result = rag_graph.invoke(state, config)

    assert "Global knowledge snippet" in result["rag_context"]
    assert result["rag_used"] == "global"


def test_rag_graph_local_flow(tmp_path, monkeypatch) -> None:
    db = Database(tmp_path / "rag.db")
    workspace_repo = WorkspaceRepository(db)
    session_repo = SessionRepository(db)
    workspace = Workspace.create("Workspace")
    workspace_repo.create(workspace)
    session = Session.create(workspace.id, title="Session")
    session_repo.create(session)

    repository = RagRepository(db)
    document = repository.create_document(
        workspace_id=workspace.id,
        source_type="chatpdf",
        source_name="ChatPdfDoc",
        content_hash="hash",
    )
    repository.attach_document_to_session(document.id, session.id)
    repository.replace_document_chunks(
        document.id,
        [
            RagChunkInput(
                id="chunk-2",
                chunk_index=0,
                content="ChatPDF snippet",
                section_title="Local",
            )
        ],
        source_name="ChatPdfDoc",
    )

    monkeypatch.setattr(rag_nodes, "Database", lambda: db)

    state = {
        "messages": [HumanMessage(content="ChatPDF")],
        "conversation_mode": "chatpdf",
        "active_pdf_document_id": document.id,
    }
    config = {
        "configurable": {
            "rag_enabled": True,
            "rag_scope": "global",
            "session_id": session.id,
            "workspace_id": workspace.id,
            "rag_k_lex": 5,
            "rag_k_vec": 0,
        }
    }
    result = rag_graph.invoke(state, config)

    assert "ChatPDF snippet" in result["rag_context"]
    assert result["rag_used"] == "local"
