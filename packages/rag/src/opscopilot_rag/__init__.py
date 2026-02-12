from .chunking import chunk_text
from .citations import build_citations
from .embeddings import EmbeddingAdapter, OpenAIEmbeddingAdapter
from .indexing import build_index_documents, bulk_upsert_chunks
from .ingestion import discover_document_paths, load_documents, normalize_text
from .opensearch_client import (
    OpenSearchClient,
    build_index_body,
    ensure_index,
    opensearch_config_from_env,
)
from .retrieval import build_knn_query, retrieve_knn
from .types import (
    Chunk,
    Citation,
    Document,
    EmbeddingRequest,
    EmbeddingResult,
    IndexedChunk,
    OpenSearchConfig,
    RetrievalResult,
)

__all__ = [
    "Chunk",
    "Citation",
    "Document",
    "EmbeddingAdapter",
    "EmbeddingRequest",
    "EmbeddingResult",
    "IndexedChunk",
    "OpenAIEmbeddingAdapter",
    "OpenSearchClient",
    "OpenSearchConfig",
    "RetrievalResult",
    "build_citations",
    "build_index_body",
    "build_index_documents",
    "build_knn_query",
    "bulk_upsert_chunks",
    "chunk_text",
    "discover_document_paths",
    "ensure_index",
    "opensearch_config_from_env",
    "load_documents",
    "normalize_text",
    "retrieve_knn",
]
