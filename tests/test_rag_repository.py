"""Tests for RAG repository behavior."""

from core.models import Session, Workspace
from core.persistence import Database, SessionRepository, WorkspaceRepository
from core.persistence.rag_repository import RagChunkInput, RagRepository


def test_rag_repository_fts_sync(tmp_path) -> None:
    db = Database(tmp_path / "test.db")
    workspace_repo = WorkspaceRepository(db)
    session_repo = SessionRepository(db)

    workspace = Workspace.create("RAG Workspace")
    workspace_repo.create(workspace)
    session = Session.create(workspace.id, title="Session")
    session_repo.create(session)

    repository = RagRepository(db)
    document = repository.create_document(
        workspace_id=workspace.id,
        source_type="artifact",
        source_name="Doc",
        content_hash="hash",
    )
    chunk = RagChunkInput(
        id="chunk-1",
        chunk_index=0,
        content="hello world from rag",
        section_title="Intro",
    )
    repository.replace_document_chunks(document.id, [chunk], source_name="Doc")

    results = repository.search_lexical(
        query="hello",
        scope="workspace",
        workspace_id=workspace.id,
        session_id=None,
        limit=5,
    )
    assert results
    assert results[0][0] == "chunk-1"


def test_rag_repository_global_scope_search(tmp_path) -> None:
    db = Database(tmp_path / "test.db")
    repository = RagRepository(db)
    document = repository.create_document(
        workspace_id="GLOBAL",
        source_type="pdf",
        source_name="GlobalDoc",
        content_hash="hash",
    )
    chunk = RagChunkInput(
        id="chunk-global",
        chunk_index=0,
        content="global knowledge base content",
        section_title="Global",
    )
    repository.replace_document_chunks(document.id, [chunk], source_name="GlobalDoc")

    results = repository.search_lexical(
        query="global",
        scope="global",
        workspace_id=None,
        session_id=None,
        limit=5,
    )
    assert results
    assert results[0][0] == "chunk-global"


def test_rag_repository_session_scope_search(tmp_path) -> None:
    db = Database(tmp_path / "test.db")
    workspace_repo = WorkspaceRepository(db)
    session_repo = SessionRepository(db)

    workspace = Workspace.create("Session Workspace")
    workspace_repo.create(workspace)
    session = Session.create(workspace.id, title="Session")
    session_repo.create(session)

    repository = RagRepository(db)
    document = repository.create_document(
        workspace_id=workspace.id,
        source_type="artifact",
        source_name="SessionDoc",
        content_hash="hash",
    )
    repository.attach_document_to_session(document.id, session.id)
    chunk = RagChunkInput(
        id="chunk-session",
        chunk_index=0,
        content="session scoped content",
        section_title="Session",
    )
    repository.replace_document_chunks(document.id, [chunk], source_name="SessionDoc")

    results = repository.search_lexical(
        query="session",
        scope="session",
        workspace_id=None,
        session_id=session.id,
        limit=5,
    )
    assert results
    assert results[0][0] == "chunk-session"


def test_rag_repository_registry_upsert_replaces_hash(tmp_path) -> None:
    db = Database(tmp_path / "test.db")
    repository = RagRepository(db)

    repository.upsert_registry_entry(
        source_path="file.pdf",
        content_hash="hash1",
        status="indexed",
        retry_count=0,
        embedding_model="model-a",
    )
    repository.upsert_registry_entry(
        source_path="file.pdf",
        content_hash="hash2",
        status="error",
        retry_count=1,
        embedding_model="model-b",
    )
    entries = repository.list_registry_entries()
    assert len(entries) == 1
    assert entries[0].content_hash == "hash2"
    assert entries[0].embedding_model == "model-b"
