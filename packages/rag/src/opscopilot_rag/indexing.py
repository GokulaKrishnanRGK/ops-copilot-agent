from __future__ import annotations

import logging

from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk

from .types import Chunk, EmbeddingResult, IndexedChunk

logger = logging.getLogger(__name__)


def build_index_documents(
    chunks: list[Chunk],
    embeddings: EmbeddingResult,
) -> list[IndexedChunk]:
    logger.info(
        "Building index documents chunks=%d embedding_vectors=%d",
        len(chunks),
        len(embeddings.vectors),
    )
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
    logger.info(
        "Upserting chunks into OpenSearch index=%s documents=%d",
        index_name,
        len(documents),
    )
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
    logger.debug(
        "OpenSearch bulk upsert completed index=%s success=%d",
        index_name,
        success,
    )
    return success
