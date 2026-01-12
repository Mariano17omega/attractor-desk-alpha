"""RAG document loading, chunking, and indexing services."""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import httpx
from PySide6.QtCore import QObject, Signal, QThread

logger = logging.getLogger(__name__)


class OpenRouterEmbeddings:
    """Custom embeddings class that uses OpenRouter API.
    
    LangChain-compatible embeddings implementation using httpx.
    """
    
    OPENROUTER_API_URL = "https://openrouter.ai/api/v1/embeddings"
    DEFAULT_MODEL = "sentence-transformers/all-minilm-l12-v2"
    
    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        batch_size: int = 20,
        timeout: float = 60.0,
    ):
        """Initialize OpenRouter embeddings.
        
        Args:
            api_key: OpenRouter API key.
            model: Embedding model ID (default: openai/text-embedding-3-small).
            batch_size: Batch size for embedding requests.
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key
        self.model = model
        self.batch_size = batch_size
        self.timeout = timeout
    
    def _get_headers(self) -> dict:
        """Get request headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://attractor-desk.app",
            "X-Title": "Attractor Desk",
        }
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents.
        
        Args:
            texts: List of text strings to embed.
            
        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []
        
        embeddings = []
        # Process in batches to avoid token limits
        
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = self._embed_batch(batch)
            embeddings.extend(batch_embeddings)
        
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query text.
        
        Args:
            text: Text string to embed.
            
        Returns:
            Embedding vector.
        """
        result = self._embed_batch([text])
        return result[0] if result else []
    
    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts.
        
        Args:
            texts: List of text strings.
            
        Returns:
            List of embedding vectors.
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self.OPENROUTER_API_URL,
                    headers=self._get_headers(),
                    json={
                        "model": self.model,
                        "input": texts,
                    },
                )
                response.raise_for_status()
                data = response.json()
                
                # Extract embeddings from response
                embeddings = []
                for item in data.get("data", []):
                    embeddings.append(item.get("embedding", []))
                
                return embeddings
                
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter embeddings API error: {e.response.status_code}")
            logger.error(f"Response: {e.response.text}")
            raise
        except Exception as e:
            logger.exception("Failed to get embeddings from OpenRouter")
            raise


@dataclass
class DocumentChunk:
    """A chunk of a document with metadata."""
    
    content: str
    source_file: str
    page_number: Optional[int] = None
    chunk_index: int = 0
    
    @property
    def metadata(self) -> dict:
        """Get metadata dict for vector store."""
        meta = {
            "source": self.source_file,
            "chunk_index": self.chunk_index,
        }
        if self.page_number is not None:
            meta["page"] = self.page_number
        return meta


@dataclass
class RagDocument:
    """Represents a loaded document with chunks."""
    
    file_path: str
    chunks: List[DocumentChunk] = field(default_factory=list)
    error: Optional[str] = None


def load_documents_from_directory(
    directory: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[RagDocument]:
    """Load and chunk all supported documents from a directory.
    
    Args:
        directory: Path to the directory containing documents.
        chunk_size: Size of each text chunk.
        chunk_overlap: Overlap between consecutive chunks.
        
    Returns:
        List of RagDocument objects with their chunks.
    """
    documents = []
    supported_extensions = {".pdf", ".txt", ".md"}
    
    dir_path = Path(directory)
    if not dir_path.exists():
        logger.warning(f"Directory does not exist: {directory}")
        return documents
    
    for file_path in dir_path.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
            doc = load_single_document(str(file_path), chunk_size, chunk_overlap)
            documents.append(doc)
    
    return documents


def load_single_document(
    file_path: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> RagDocument:
    """Load and chunk a single document.
    
    Args:
        file_path: Path to the document.
        chunk_size: Size of each text chunk.
        chunk_overlap: Overlap between consecutive chunks.
        
    Returns:
        RagDocument with chunks or error.
    """
    doc = RagDocument(file_path=file_path)
    path = Path(file_path)
    suffix = path.suffix.lower()
    
    try:
        if suffix == ".pdf":
            chunks = _load_pdf(path, chunk_size, chunk_overlap)
        elif suffix in {".txt", ".md"}:
            chunks = _load_text(path, chunk_size, chunk_overlap)
        else:
            doc.error = f"Unsupported file type: {suffix}"
            return doc
        
        doc.chunks = chunks
        
    except Exception as e:
        logger.exception(f"Error loading {file_path}")
        doc.error = str(e)
    
    return doc


def _load_pdf(
    path: Path,
    chunk_size: int,
    chunk_overlap: int,
) -> List[DocumentChunk]:
    """Load a PDF file using LangChain loaders."""
    try:
        from langchain_community.document_loaders import PyPDFLoader
        loader = PyPDFLoader(str(path))
    except ImportError:
        # Fallback to PDFPlumberLoader
        try:
            from langchain_community.document_loaders import PDFPlumberLoader
            loader = PDFPlumberLoader(str(path))
        except ImportError:
            raise ImportError("No PDF loader available. Install pypdf or pdfplumber.")
    
    pages = loader.load()
    chunks = []
    
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    
    for page in pages:
        page_num = page.metadata.get("page", 0) + 1  # 1-indexed
        page_chunks = splitter.split_text(page.page_content)
        
        for i, chunk_text in enumerate(page_chunks):
            chunks.append(DocumentChunk(
                content=chunk_text,
                source_file=str(path),
                page_number=page_num,
                chunk_index=len(chunks),
            ))
    
    return chunks


def _load_text(
    path: Path,
    chunk_size: int,
    chunk_overlap: int,
) -> List[DocumentChunk]:
    """Load a text/markdown file and split into chunks."""
    try:
        from langchain_community.document_loaders import TextLoader
        loader = TextLoader(str(path), encoding="utf-8")
        docs = loader.load()
    except Exception:
        # Fallback to direct file reading
        text = path.read_text(encoding="utf-8")
        from langchain_core.documents import Document
        docs = [Document(page_content=text, metadata={"source": str(path)})]
    
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    
    chunks = []
    for doc in docs:
        text_chunks = splitter.split_text(doc.page_content)
        for i, chunk_text in enumerate(text_chunks):
            chunks.append(DocumentChunk(
                content=chunk_text,
                source_file=str(path),
                page_number=None,
                chunk_index=len(chunks),
            ))
    
    return chunks


class DocumentLoaderWorker(QThread):
    """Worker thread for loading documents in the background."""
    
    progress = Signal(int, int)  # current, total
    document_loaded = Signal(str)  # file path
    completed = Signal(list)  # List[RagDocument]
    error = Signal(str)
    
    def __init__(
        self,
        directory: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.directory = directory
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._cancelled = False
    
    def cancel(self) -> None:
        """Cancel the loading operation."""
        self._cancelled = True
    
    def run(self) -> None:
        """Load documents in the background."""
        try:
            documents = []
            supported_extensions = {".pdf", ".txt", ".md"}
            
            dir_path = Path(self.directory)
            if not dir_path.exists():
                self.error.emit(f"Directory does not exist: {self.directory}")
                return
            
            # Collect files first
            files = [
                f for f in dir_path.rglob("*")
                if f.is_file() and f.suffix.lower() in supported_extensions
            ]
            
            total = len(files)
            for i, file_path in enumerate(files):
                if self._cancelled:
                    break
                
                self.progress.emit(i + 1, total)
                self.document_loaded.emit(str(file_path))
                
                doc = load_single_document(
                    str(file_path),
                    self.chunk_size,
                    self.chunk_overlap,
                )
                documents.append(doc)
            
            if not self._cancelled:
                self.completed.emit(documents)
                
        except Exception as e:
            logger.exception("Error loading documents")
            self.error.emit(str(e))


@dataclass
class RetrievalResult:
    """Result from a RAG retrieval query."""
    
    content: str
    source_file: str
    page_number: Optional[int] = None
    score: float = 0.0
    
    @property
    def citation(self) -> str:
        """Format citation for display."""
        base = Path(self.source_file).name
        if self.page_number:
            return f"{base} (p. {self.page_number})"
        return base


class ChromaIndexService:
    """Service for managing the Chroma vector index."""
    
    DEFAULT_INDEX_PATH = Path.home() / ".attractor_desk" / "rag_index"
    
    def __init__(
        self,
        index_path: Optional[Path] = None,
        embedding_model: str = "openai/text-embedding-3-small",
        embedding_batch_size: int = 20,
        api_key: Optional[str] = None,
    ):
        """Initialize the Chroma index service.
        
        Args:
            index_path: Path to persist the index. Uses default if None.
            embedding_model: Model ID for embeddings.
            embedding_batch_size: Batch size for embeddings.
            api_key: OpenRouter API key for embeddings.
        """
        self.index_path = index_path or self.DEFAULT_INDEX_PATH
        self.embedding_model = embedding_model
        self.embedding_batch_size = embedding_batch_size
        self.api_key = api_key
        self._vector_store = None
        self._embeddings = None
    
    @property
    def index_exists(self) -> bool:
        """Check if the index exists on disk."""
        chroma_dir = self.index_path / "chroma.sqlite3"
        return chroma_dir.exists() or (self.index_path / "chroma.sqlite3").exists()
    
    @property
    def is_loaded(self) -> bool:
        """Check if the vector store is loaded."""
        return self._vector_store is not None
    
    def _get_embeddings(self):
        """Get or create embeddings function.
        
        Uses OpenRouter API for embeddings.
        """
        if self._embeddings is None:
            if not self.api_key:
                raise ValueError(
                    "OpenRouter API key is required for embeddings. "
                    "Please configure your API key in Settings → Models."
                )
            self._embeddings = OpenRouterEmbeddings(
                api_key=self.api_key,
                model=self.embedding_model or OpenRouterEmbeddings.DEFAULT_MODEL,
                batch_size=self.embedding_batch_size,
            )
        return self._embeddings
    
    def load_index(self) -> bool:
        """Load the existing index from disk.
        
        Returns:
            True if loaded successfully, False otherwise.
        """
        if not self.index_exists:
            return False
        
        try:
            from langchain_chroma import Chroma
            self._vector_store = Chroma(
                persist_directory=str(self.index_path),
                embedding_function=self._get_embeddings(),
            )
            return True
        except Exception as e:
            logger.exception("Failed to load Chroma index")
            return False
    
    def add_documents(self, chunks: List[DocumentChunk]) -> bool:
        """Add documents to the index.
        
        Args:
            chunks: List of document chunks to add.
            
        Returns:
            True if added successfully, False otherwise.
        """
        try:
            from langchain_chroma import Chroma
            from langchain_core.documents import Document
            
            # Ensure directory exists
            self.index_path.mkdir(parents=True, exist_ok=True)
            
            # Convert chunks to LangChain documents
            lc_docs = [
                Document(page_content=chunk.content, metadata=chunk.metadata)
                for chunk in chunks
            ]
            
            if not lc_docs:
                return True
            
            if self._vector_store is None:
                # Create new vector store
                self._vector_store = Chroma.from_documents(
                    documents=lc_docs,
                    embedding=self._get_embeddings(),
                    persist_directory=str(self.index_path),
                )
            else:
                # Add to existing
                self._vector_store.add_documents(lc_docs)
            
            return True
            
        except Exception as e:
            logger.exception("Failed to add documents to Chroma index")
            return False

    def create_index(self, chunks: List[DocumentChunk]) -> bool:
        """Create a new index from document chunks.
        
        Args:
            chunks: List of document chunks to index.
            
        Returns:
            True if created successfully, False otherwise.
        """
        return self.add_documents(chunks)
    
    def clear_index(self) -> bool:
        """Clear the existing index.
        
        Returns:
            True if cleared successfully, False otherwise.
        """
        try:
            import shutil
            if self.index_path.exists():
                shutil.rmtree(self.index_path)
            self._vector_store = None
            return True
        except Exception as e:
            logger.exception("Failed to clear index")
            return False
    
    def query(
        self,
        query: str,
        top_k: int = 4,
    ) -> List[RetrievalResult]:
        """Query the index for relevant documents.
        
        Args:
            query: The query string.
            top_k: Number of results to return.
            
        Returns:
            List of RetrievalResult objects.
        """
        if not self.is_loaded:
            if not self.load_index():
                return []
        
        try:
            results = self._vector_store.similarity_search_with_score(query, k=top_k)
            
            retrieval_results = []
            for doc, score in results:
                result = RetrievalResult(
                    content=doc.page_content,
                    source_file=doc.metadata.get("source", "Unknown"),
                    page_number=doc.metadata.get("page"),
                    score=float(score),
                )
                retrieval_results.append(result)
            
            return retrieval_results
            
        except Exception as e:
            logger.exception("Query failed")
            return []


class IndexingWorker(QThread):
    """Worker thread for indexing documents."""
    
    progress = Signal(int, int)  # current, total
    indexing_file = Signal(str)
    completed = Signal(bool, int)  # success, num_chunks
    error = Signal(str)
    
    def __init__(
        self,
        documents: List[RagDocument],
        index_service: ChromaIndexService,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.documents = documents
        self.index_service = index_service
        self._cancelled = False
    
    def cancel(self) -> None:
        self._cancelled = True
    
    def run(self) -> None:
        try:
            # Collect all chunks
            all_chunks = []
            total = len(self.documents)
            
            for i, doc in enumerate(self.documents):
                if self._cancelled:
                    break
                
            for i, doc in enumerate(self.documents):
                if self._cancelled:
                    break
                
                # self.progress.emit(i + 1, total) # Removed: progress is now granular
                self.indexing_file.emit(doc.file_path)
                
                if not doc.error:
                    all_chunks.extend(doc.chunks)
            
            if self._cancelled:
                return
            
            # Index in batches
            total_chunks = len(all_chunks)
            processed_chunks = 0
            # Use the embedding batch size as the processing batch size
            batch_size = self.index_service.embedding_batch_size
            
            for i in range(0, total_chunks, batch_size):
                if self._cancelled:
                    break
                    
                batch = all_chunks[i:i + batch_size]
                if not self.index_service.add_documents(batch):
                    raise Exception("Failed to add batch to index")
                
                processed_chunks += len(batch)
                self.progress.emit(processed_chunks, total_chunks)
            
            self.completed.emit(True, processed_chunks)
            
        except Exception as e:
            logger.exception("Indexing failed")
            self.error.emit(str(e))


class RetrievalWorker(QThread):
    """Worker thread for retrieval queries."""
    
    completed = Signal(list)  # List[RetrievalResult]
    error = Signal(str)
    
    def __init__(
        self,
        query: str,
        index_service: ChromaIndexService,
        top_k: int = 4,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.query_text = query
        self.index_service = index_service
        self.top_k = top_k
    
    def run(self) -> None:
        try:
            results = self.index_service.query(self.query_text, self.top_k)
            self.completed.emit(results)
        except Exception as e:
            logger.exception("Retrieval failed")
            self.error.emit(str(e))


class RagService(QObject):
    """Main RAG service coordinating loading, indexing, and retrieval."""
    
    # Status signals
    status_changed = Signal(str)  # status message
    index_ready = Signal(bool)  # is_ready
    
    # Indexing signals
    indexing_started = Signal()
    indexing_progress = Signal(int, int)  # current, total
    indexing_completed = Signal(bool, int)  # success, num_chunks
    indexing_error = Signal(str)
    
    # Retrieval signals
    retrieval_completed = Signal(list)  # List[RetrievalResult]
    retrieval_error = Signal(str)
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._api_key = api_key
        self._index_service: Optional[ChromaIndexService] = None
        self._loader_worker: Optional[DocumentLoaderWorker] = None
        self._indexing_worker: Optional[IndexingWorker] = None
        self._retrieval_worker: Optional[RetrievalWorker] = None
        self._is_indexing = False
        
        # Default settings
        self._knowledge_base_path = str(Path.home() / "Documents" / "Doc_RAG")
        self._chunk_size = 1000
        self._chunk_overlap = 200
        self._top_k = 4
        self._embedding_model = None
        self._embedding_batch_size = 20
    
    @property
    def is_ready(self) -> bool:
        """Check if RAG is ready for queries."""
        if self._index_service is None:
            return False
        return self._index_service.is_loaded or self._index_service.index_exists
    
    @property
    def is_indexing(self) -> bool:
        """Check if indexing is in progress."""
        return self._is_indexing
    
    def configure(
        self,
        knowledge_base_path: str,
        chunk_size: int,
        chunk_overlap: int,
        top_k: int,
        embedding_model: str,
        embedding_batch_size: int = 20,
        api_key: Optional[str] = None,
    ) -> None:
        """Configure RAG settings.
        
        Args:
            knowledge_base_path: Path to knowledge base folder.
            chunk_size: Chunk size for splitting.
            chunk_overlap: Overlap between chunks.
            top_k: Number of results for retrieval.
            embedding_model: Model for embeddings.
            embedding_batch_size: Batch size for embeddings.
            api_key: API key for OpenRouter.
        """
        self._knowledge_base_path = knowledge_base_path
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._top_k = top_k
        self._embedding_model = embedding_model
        self._embedding_batch_size = embedding_batch_size
        if api_key:
            self._api_key = api_key
        
        # Recreate index service with new settings
        self._index_service = ChromaIndexService(
            embedding_model=self._embedding_model,
            embedding_batch_size=self._embedding_batch_size,
            api_key=self._api_key,
        )
        
        # Check if index already exists
        if self._index_service.index_exists:
            if self._index_service.load_index():
                self.status_changed.emit("Index loaded")
                self.index_ready.emit(True)
    
    def ensure_knowledge_base_path(self) -> bool:
        """Ensure the knowledge base folder exists.
        
        Returns:
            True if the folder exists or was created.
        """
        try:
            path = Path(self._knowledge_base_path)
            path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.exception("Failed to create knowledge base folder")
            return False
    
    def reindex(self) -> None:
        """Start a full reindex of the knowledge base."""
        if self._is_indexing:
            return
        if not self._embedding_model:
            self.indexing_error.emit("RAG not configured: embedding model is missing")
            return
        
        self._is_indexing = True
        self.indexing_started.emit()
        self.status_changed.emit("Loading documents...")
        
        # Ensure index service exists
        if self._index_service is None:
            self._index_service = ChromaIndexService(
                embedding_model=self._embedding_model,
                embedding_batch_size=self._embedding_batch_size,
                api_key=self._api_key,
            )
        
        # Clear existing index
        self._index_service.clear_index()
        
        # Start document loading
        self._loader_worker = DocumentLoaderWorker(
            directory=self._knowledge_base_path,
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
            parent=self,
        )
        self._loader_worker.progress.connect(self._on_loading_progress)
        self._loader_worker.completed.connect(self._on_loading_completed)
        self._loader_worker.error.connect(self._on_loading_error)
        self._loader_worker.start()
    
    def _on_loading_progress(self, current: int, total: int) -> None:
        self.status_changed.emit(f"Loading documents: {current}/{total}")
        self.indexing_progress.emit(current, total)
    
    def _on_loading_completed(self, documents: List[RagDocument]) -> None:
        self.status_changed.emit("Indexing documents...")
        
        # Start indexing
        self._indexing_worker = IndexingWorker(
            documents=documents,
            index_service=self._index_service,
            parent=self,
        )
        self._indexing_worker.progress.connect(self.indexing_progress.emit)
        self._indexing_worker.completed.connect(self._on_indexing_completed)
        self._indexing_worker.error.connect(self._on_indexing_error)
        self._indexing_worker.start()
    
    def _on_loading_error(self, error: str) -> None:
        self._is_indexing = False
        self.status_changed.emit(f"Error: {error}")
        self.indexing_error.emit(error)
    
    def _on_indexing_completed(self, success: bool, num_chunks: int) -> None:
        self._is_indexing = False
        if success:
            self.status_changed.emit(f"Indexed {num_chunks} chunks")
            self.index_ready.emit(True)
        else:
            self.status_changed.emit("Indexing failed")
        self.indexing_completed.emit(success, num_chunks)
    
    def _on_indexing_error(self, error: str) -> None:
        self._is_indexing = False
        self.status_changed.emit(f"Error: {error}")
        self.indexing_error.emit(error)
    
    def clear_index(self) -> None:
        """Clear the current index."""
        if self._index_service:
            self._index_service.clear_index()
            self.status_changed.emit("Index cleared")
            self.index_ready.emit(False)
    
    def query(self, query_text: str) -> None:
        """Query the index asynchronously.
        
        Args:
            query_text: The query string.
        """
        if not self.is_ready:
            self.retrieval_error.emit("Index not ready")
            return
        
        self._retrieval_worker = RetrievalWorker(
            query=query_text,
            index_service=self._index_service,
            top_k=self._top_k,
            parent=self,
        )
        self._retrieval_worker.completed.connect(self.retrieval_completed.emit)
        self._retrieval_worker.error.connect(self.retrieval_error.emit)
        self._retrieval_worker.start()
    
    def query_sync(self, query_text: str) -> List[RetrievalResult]:
        """Query the index synchronously.
        
        Args:
            query_text: The query string.
            
        Returns:
            List of retrieval results.
        """
        if not self.is_ready:
            return []
        
        if self._index_service is None:
            return []
        
        try:
            return self._index_service.query(query_text, self._top_k)
        except Exception as e:
            logger.exception("Sync query failed")
            return []
    
    def cancel_indexing(self) -> None:
        """Cancel any in-progress indexing operation."""
        if self._loader_worker is not None and self._loader_worker.isRunning():
            self._loader_worker.cancel()
        if self._indexing_worker is not None and self._indexing_worker.isRunning():
            self._indexing_worker.cancel()
        self._is_indexing = False
    
    def shutdown(self) -> None:
        """Shutdown the RAG service and stop all workers.
        
        Call this before closing the application to ensure all threads
        are properly terminated.
        """
        # Cancel any in-progress operations
        self.cancel_indexing()
        
        # Wait for loader worker to finish
        if self._loader_worker is not None and self._loader_worker.isRunning():
            self._loader_worker.quit()
            self._loader_worker.wait(3000)  # Wait up to 3 seconds
            if self._loader_worker.isRunning():
                self._loader_worker.terminate()
        
        # Wait for indexing worker to finish
        if self._indexing_worker is not None and self._indexing_worker.isRunning():
            self._indexing_worker.quit()
            self._indexing_worker.wait(3000)
            if self._indexing_worker.isRunning():
                self._indexing_worker.terminate()
        
        # Wait for retrieval worker to finish
        if self._retrieval_worker is not None and self._retrieval_worker.isRunning():
            self._retrieval_worker.quit()
            self._retrieval_worker.wait(3000)
            if self._retrieval_worker.isRunning():
                self._retrieval_worker.terminate()
