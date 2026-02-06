from __future__ import annotations

from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk

from .types import Chunk, EmbeddingResult, IndexedChunk


def build_index_documents(
    chunks: list[Chunk],
    embeddings: EmbeddingResult,
) -> list[IndexedChunk]:
    if len(chunks) != len(embeddings.vectors):
        raise ValueError("chunks and embeddings length mismatch")

    documents: list[IndexedChunk] = []
    for chunk, vector in zip(chunks, embeddings.vectors):
        documents.append(
            IndexedChunk(
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                chunk_index=chunk.index,
                source=chunk.metadata.get("source", ""),
                text=chunk.text,
                metadata=chunk.metadata,
                embedding=vector,
            )
        )
    return documents


def bulk_upsert_chunks(
    client: OpenSearch,
    index_name: str,
    documents: list[IndexedChunk],
) -> int:
    actions = []
    for doc in documents:
        actions.append(
            {
                "_op_type": "index",
                "_index": index_name,
                "_id": doc.chunk_id,
                "_source": {
                    "document_id": doc.document_id,
                    "chunk_id": doc.chunk_id,
                    "chunk_index": doc.chunk_index,
                    "source": doc.source,
                    "text": doc.text,
                    "metadata": doc.metadata,
                    "embedding": doc.embedding,
                },
            }
        )
    success, _ = bulk(client, actions)
    return success
