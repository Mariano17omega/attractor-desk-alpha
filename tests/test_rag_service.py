"""Tests for RAG service helpers."""

from datetime import datetime

from core.models import Session, Workspace
from core.persistence import Database, SessionRepository, WorkspaceRepository
from core.persistence.rag_repository import RagChunkDetails, RagRepository
from core.services.rag_service import (
    RagIndexRequest,
    _heuristic_rerank,
    _index_document,
    _rrf_fuse,
)


def test_rrf_fusion_prefers_higher_rank() -> None:
    scores = _rrf_fuse([["a", "b", "c"], ["b", "c", "a"]], rrf_k=60)
    assert scores["b"] > scores["a"]


def test_heuristic_rerank_promotes_diversity() -> None:
    now = datetime.now()
    details_by_id = {
        "a1": RagChunkDetails(
            id="a1",
            document_id="doc-a",
            chunk_index=0,
            section_title="Intro",
            content="A1",
            token_count=None,
            created_at=now,
            source_name="DocA",
            source_type="artifact",
            source_path=None,
            document_updated_at=now,
        ),
        "a2": RagChunkDetails(
            id="a2",
            document_id="doc-a",
            chunk_index=1,
            section_title=None,
            content="A2",
            token_count=None,
            created_at=now,
            source_name="DocA",
            source_type="artifact",
            source_path=None,
            document_updated_at=now,
        ),
        "b1": RagChunkDetails(
            id="b1",
            document_id="doc-b",
            chunk_index=0,
            section_title=None,
            content="B1",
            token_count=None,
            created_at=now,
            source_name="DocB",
            source_type="artifact",
            source_path=None,
            document_updated_at=now,
        ),
    }
    candidates = [
        {"chunk_id": "a1", "fused_score": 0.2},
        {"chunk_id": "a2", "fused_score": 0.19},
        {"chunk_id": "b1", "fused_score": 0.18},
    ]

    reranked = _heuristic_rerank(candidates, details_by_id, scope="session")
    assert reranked[0]["chunk_id"] == "a1"
    assert reranked[1]["chunk_id"] == "b1"


def test_indexing_attaches_and_scopes(tmp_path) -> None:
    db = Database(tmp_path / "test.db")
    workspace_repo = WorkspaceRepository(db)
    session_repo = SessionRepository(db)

    workspace = Workspace.create("Workspace")
    workspace_repo.create(workspace)
    session_a = Session.create(workspace.id, title="Session A")
    session_repo.create(session_a)
    session_b = Session.create(workspace.id, title="Session B")
    session_repo.create(session_b)

    repository = RagRepository(db)
    request = RagIndexRequest(
        workspace_id=workspace.id,
        session_id=session_a.id,
        artifact_entry_id="entry-1",
        source_type="artifact",
        source_name="DocA",
        content="hello from session A",
        embeddings_enabled=False,
    )
    result = _index_document(repository, request)
    assert result.success

    session_hits = repository.search_lexical(
        query="hello",
        scope="session",
        workspace_id=None,
        session_id=session_a.id,
        limit=5,
    )
    assert session_hits

    other_hits = repository.search_lexical(
        query="hello",
        scope="session",
        workspace_id=None,
        session_id=session_b.id,
        limit=5,
    )
    assert other_hits == []

    workspace_hits = repository.search_lexical(
        query="hello",
        scope="workspace",
        workspace_id=workspace.id,
        session_id=None,
        limit=5,
    )
    assert workspace_hits
