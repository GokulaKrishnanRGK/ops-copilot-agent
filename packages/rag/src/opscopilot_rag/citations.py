from __future__ import annotations

from .types import Citation, RetrievalResult


def build_citations(results: list[RetrievalResult]) -> list[Citation]:
    citations: list[Citation] = []
    for result in results:
        citations.append(
            Citation(
                document_id=result.document_id,
                chunk_id=result.chunk_id,
                source=result.source,
                score=result.score,
                metadata=result.metadata,
            )
        )
    return citations
