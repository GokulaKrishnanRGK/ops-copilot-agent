from __future__ import annotations

import logging

from .types import Chunk

logger = logging.getLogger(__name__)


def chunk_text(
    document_id: str,
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    metadata: dict | None = None,
) -> list[Chunk]:
    logger.debug(
        "Chunking document document_id=%s text_length=%d chunk_size=%d chunk_overlap=%d",
        document_id,
        len(text),
        chunk_size,
        chunk_overlap,
    )
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be non-negative")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    chunks: list[Chunk] = []
    start = 0
    index = 0
    text_length = len(text)
    base_metadata = metadata or {}

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk_text_value = text[start:end]
        chunk_id = f"{document_id}::chunk-{index}"
        chunk_metadata = {**base_metadata, "chunk_index": index}
        chunks.append(
            Chunk(
                document_id=document_id,
                chunk_id=chunk_id,
                index=index,
                text=chunk_text_value,
                metadata=chunk_metadata,
            )
        )
        if end == text_length:
            break
        start = end - chunk_overlap
        index += 1

    logger.info(
        "Chunking completed document_id=%s chunks=%d",
        document_id,
        len(chunks),
    )
    return chunks
