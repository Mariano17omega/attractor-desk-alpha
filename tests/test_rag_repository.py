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
