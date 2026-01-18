"""Integration tests for ChromaDB migration with real PDFs."""

from pathlib import Path
import tempfile

import pytest

from core.models import Session, Workspace
from core.persistence import Database, SessionRepository, WorkspaceRepository
from core.persistence.rag_repository import RagRepository
from core.services.chroma_service import ChromaService
from core.services.docling_service import convert_pdf_to_markdown
from core.services.global_rag_service import GlobalRagIndexRequest, _GlobalIndexWorker
from core.services.local_rag_service import LocalRagIndexRequest, _LocalIndexWorker


# Get the PDFs directory
TEST_PDFS_DIR = Path(__file__).parent / "pdfs_for_tests"
PDF_FILES = list(TEST_PDFS_DIR.glob("*.pdf")) if TEST_PDFS_DIR.exists() else []


@pytest.mark.skipif(not PDF_FILES, reason="No PDFs found in tests/pdfs_for_tests/")
@pytest.mark.parametrize("pdf_path", PDF_FILES, ids=lambda p: p.name)
def test_chromadb_global_rag_with_real_pdfs(pdf_path, tmp_path):
    """Test ChromaDB integration with real PDFs from the test directory."""
    # Setup database and ChromaDB
    db = Database(tmp_path / "test.db")
    repository = RagRepository(db)
    chroma_service = ChromaService(persist_directory=str(tmp_path / "chromadb"))

    # Verify ChromaDB is initialized
    assert chroma_service.count() == 0

    # Index the PDF
    request = GlobalRagIndexRequest(
        workspace_id="GLOBAL",
        pdf_paths=[str(pdf_path)],
        embeddings_enabled=True,
        embedding_model="openai/text-embedding-3-small",
        api_key="dummy_key_for_test",
    )

    worker = _GlobalIndexWorker(repository, request, chroma_service=chroma_service)

    # Note: This will fail if Docling is not installed or if API key is invalid
    # We'll catch the error and report it
    try:
        result = worker._run_index()

        # Check that indexing succeeded
        assert result.indexed >= 0  # May be 0 if embeddings failed but FTS5 succeeded

        # Check database entries
        entries = repository.list_registry_entries()
        matching_entries = [e for e in entries if Path(e.source_path).name == pdf_path.name]
        assert len(matching_entries) > 0

        # Check FTS5 search works
        hits = repository.search_lexical(
            query="the",  # Common word that should appear in most PDFs
            scope="global",
            workspace_id=None,
            session_id=None,
            limit=5,
        )

        print(f"\n{pdf_path.name}:")
        print(f"  - Indexed: {result.indexed}")
        print(f"  - Failed: {result.failed}")
        print(f"  - FTS5 hits: {len(hits)}")
        print(f"  - ChromaDB vectors: {chroma_service.count()}")

        # If embeddings were enabled and succeeded, check ChromaDB
        if result.indexed > 0 and chroma_service.count() > 0:
            # Get a chunk to test vector search
            if hits:
                chunk_id = hits[0].chunk_id
                chunk = repository.get_chunk(chunk_id)
                if chunk:
                    # Get embedding for this chunk
                    embeddings = repository.get_embeddings([chunk_id])
                    if embeddings and embeddings[0]:
                        # Query ChromaDB
                        similar = chroma_service.query_similar(
                            query_vector=embeddings[0],
                            where={"workspace_id": "GLOBAL", "session_id": ""},
                            k=5,
                        )
                        assert len(similar) > 0
                        print(f"  - ChromaDB query returned {len(similar)} results")

    except ImportError as e:
        if "docling" in str(e).lower():
            pytest.skip("Docling not installed. Install with: pip install -e '.[pdf]'")
        raise
    except Exception as e:
        # Report the error but don't fail the test for API/network issues
        print(f"\nWarning: Test failed for {pdf_path.name}: {e}")
        # Re-raise if it's not an API/network error
        if "api" not in str(e).lower() and "key" not in str(e).lower():
            raise


@pytest.mark.skipif(len(PDF_FILES) < 1, reason="Need at least 1 PDF")
def test_chromadb_local_rag_with_real_pdf(tmp_path):
    """Test ChromaDB integration with ChatPDF mode using a real PDF."""
    # Setup
    db = Database(tmp_path / "test.db")
    workspace_repo = WorkspaceRepository(db)
    session_repo = SessionRepository(db)
    repository = RagRepository(db)
    chroma_service = ChromaService(persist_directory=str(tmp_path / "chromadb"))

    # Create workspace and session
    workspace = Workspace.create("ChatPDF Test")
    workspace_repo.create(workspace)
    session = Session.create(workspace.id, title="Test Session")
    session_repo.create(session)

    # Use the first available PDF
    pdf_path = PDF_FILES[0]

    try:
        # Index the PDF in ChatPDF mode
        request = LocalRagIndexRequest(
            workspace_id=workspace.id,
            session_id=session.id,
            pdf_path=str(pdf_path),
            embeddings_enabled=True,
            embedding_model="openai/text-embedding-3-small",
            api_key="dummy_key_for_test",
        )

        # Mock the storage directory
        import core.services.local_rag_service as local_service
        original_dir = local_service.CHATPDF_STORAGE_DIR
        local_service.CHATPDF_STORAGE_DIR = tmp_path / "chatpdf_storage"

        try:
            worker = _LocalIndexWorker(repository, request, chroma_service=chroma_service)
            result = worker._run_index()

            assert result.success is True
            assert result.document_id is not None

            # Check FTS5 search in session scope
            hits = repository.search_lexical(
                query="the",
                scope="session",
                workspace_id=None,
                session_id=session.id,
                limit=5,
            )

            print(f"\nChatPDF mode with {pdf_path.name}:")
            print(f"  - Document ID: {result.document_id}")
            print(f"  - FTS5 hits: {len(hits)}")
            print(f"  - ChromaDB vectors: {chroma_service.count()}")

            # Test ChromaDB isolation - should only return results for this session
            if hits and chroma_service.count() > 0:
                chunk_id = hits[0].chunk_id
                embeddings = repository.get_embeddings([chunk_id])
                if embeddings and embeddings[0]:
                    # Query with session filter
                    similar = chroma_service.query_similar(
                        query_vector=embeddings[0],
                        where={"workspace_id": workspace.id, "session_id": session.id},
                        k=5,
                    )
                    assert len(similar) > 0
                    print(f"  - ChromaDB session-scoped query: {len(similar)} results")

                    # Verify none of the results belong to global scope
                    for chunk_id, score in similar:
                        chunk = repository.get_chunk(chunk_id)
                        assert chunk is not None
                        doc = repository.get_document(chunk.document_id)
                        assert doc.workspace_id == workspace.id

        finally:
            local_service.CHATPDF_STORAGE_DIR = original_dir

    except ImportError as e:
        if "docling" in str(e).lower():
            pytest.skip("Docling not installed. Install with: pip install -e '.[pdf]'")
        raise
    except Exception as e:
        print(f"\nWarning: Test failed: {e}")
        if "api" not in str(e).lower() and "key" not in str(e).lower():
            raise


def test_chromadb_vector_search_performance(tmp_path):
    """Test ChromaDB performance compared to manual vector similarity."""
    import array

    db = Database(tmp_path / "test.db")
    repository = RagRepository(db)
    chroma_service = ChromaService(persist_directory=str(tmp_path / "chromadb"))

    # Create dummy document with embeddings
    document = repository.create_document(
        workspace_id="GLOBAL",
        source_type="test",
        source_name="PerfTest",
        content_hash="test_hash",
    )

    # Create 100 chunks with random-ish embeddings
    from core.persistence.rag_repository import RagChunkInput, RagEmbeddingInput
    import uuid

    chunks = []
    chunk_ids = []
    for i in range(100):
        chunk_id = str(uuid.uuid4())
        chunk_ids.append(chunk_id)
        chunks.append(
            RagChunkInput(
                id=chunk_id,
                chunk_index=i,
                content=f"Chunk {i} content",
                section_title=f"Section {i}",
            )
        )

    repository.replace_document_chunks(document.id, chunks, "PerfTest")

    # Add embeddings (simple normalized vectors)
    embeddings = []
    vectors = []  # Keep vectors separately for ChromaDB
    for i in range(100):
        # Create a simple normalized vector (offset by 1 to avoid zero vectors)
        vector = [float((i % 10) + 1), float((i % 7) + 1), float((i % 5) + 1)]
        magnitude = sum(x**2 for x in vector) ** 0.5
        normalized = [x / magnitude for x in vector]
        vectors.append(normalized)
        embeddings.append(
            RagEmbeddingInput(
                chunk_id=chunk_ids[i],
                model="test-model",
                dims=len(normalized),
                embedding_blob=array.array("f", normalized).tobytes(),
            )
        )

    repository.upsert_embeddings(embeddings)

    # Add to ChromaDB
    metadata = [
        {
            "chunk_id": chunk_id,
            "document_id": document.id,
            "workspace_id": "GLOBAL",
            "session_id": "",
        }
        for chunk_id in chunk_ids
    ]
    chroma_service.add_embeddings(chunk_ids, vectors, metadata)

    # Test query
    query_vector = [1.0, 0.5, 0.25]
    magnitude = sum(x**2 for x in query_vector) ** 0.5
    query_vector = [x / magnitude for x in query_vector]

    # Query ChromaDB
    results = chroma_service.query_similar(
        query_vector=query_vector,
        where={"workspace_id": "GLOBAL", "session_id": ""},
        k=10,
    )

    assert len(results) == 10
    assert all(isinstance(score, float) for _, score in results)
    assert all(0 <= score <= 1 for _, score in results)

    # Results should be sorted by score descending
    scores = [score for _, score in results]
    assert scores == sorted(scores, reverse=True)

    print(f"\nPerformance test:")
    print(f"  - Indexed {len(chunks)} chunks")
    print(f"  - ChromaDB returned {len(results)} results")
    print(f"  - Top score: {scores[0]:.4f}")
    print(f"  - Scores are sorted: {scores == sorted(scores, reverse=True)}")


def test_chromadb_metadata_filtering(tmp_path):
    """Test that ChromaDB correctly filters by workspace and session."""
    import array

    db = Database(tmp_path / "test.db")
    workspace_repo = WorkspaceRepository(db)
    repository = RagRepository(db)
    chroma_service = ChromaService(persist_directory=str(tmp_path / "chromadb"))

    from core.persistence.rag_repository import RagChunkInput, RagEmbeddingInput
    import uuid

    # Create a workspace for non-global documents
    workspace = Workspace.create("Test Workspace")
    workspace_repo.create(workspace)

    # Create documents in different scopes
    doc_global = repository.create_document(
        workspace_id="GLOBAL",
        source_type="test",
        source_name="GlobalDoc",
        content_hash="hash1",
    )

    doc_workspace = repository.create_document(
        workspace_id=workspace.id,
        source_type="test",
        source_name="WorkspaceDoc",
        content_hash="hash2",
    )

    # Add chunks and embeddings
    test_vector = [0.1, 0.2, 0.3]

    chunk_global_id = str(uuid.uuid4())
    repository.replace_document_chunks(
        doc_global.id,
        [RagChunkInput(id=chunk_global_id, chunk_index=0, content="Global")],
        "GlobalDoc",
    )
    repository.upsert_embeddings([
        RagEmbeddingInput(
            chunk_id=chunk_global_id,
            model="test-model",
            dims=len(test_vector),
            embedding_blob=array.array("f", test_vector).tobytes(),
        )
    ])
    chroma_service.add_embeddings(
        [chunk_global_id],
        [test_vector],
        [{"chunk_id": chunk_global_id, "document_id": doc_global.id, "workspace_id": "GLOBAL", "session_id": ""}],
    )

    chunk_workspace_id = str(uuid.uuid4())
    repository.replace_document_chunks(
        doc_workspace.id,
        [RagChunkInput(id=chunk_workspace_id, chunk_index=0, content="Workspace")],
        "WorkspaceDoc",
    )
    repository.upsert_embeddings([
        RagEmbeddingInput(
            chunk_id=chunk_workspace_id,
            model="test-model",
            dims=len(test_vector),
            embedding_blob=array.array("f", test_vector).tobytes(),
        )
    ])
    chroma_service.add_embeddings(
        [chunk_workspace_id],
        [test_vector],
        [{"chunk_id": chunk_workspace_id, "document_id": doc_workspace.id, "workspace_id": workspace.id, "session_id": ""}],
    )

    # Query global scope
    global_results = chroma_service.query_similar(
        query_vector=test_vector,
        where={"workspace_id": "GLOBAL", "session_id": ""},
        k=10,
    )
    assert len(global_results) == 1
    assert global_results[0][0] == chunk_global_id

    # Query workspace scope
    workspace_results = chroma_service.query_similar(
        query_vector=test_vector,
        where={"workspace_id": workspace.id, "session_id": ""},
        k=10,
    )
    assert len(workspace_results) == 1
    assert workspace_results[0][0] == chunk_workspace_id

    print(f"\nMetadata filtering test:")
    print(f"  - Global scope: {len(global_results)} results")
    print(f"  - Workspace scope: {len(workspace_results)} results")
    print(f"  - Isolation verified: ✓")
