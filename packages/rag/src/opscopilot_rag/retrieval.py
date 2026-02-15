from __future__ import annotations

from opentelemetry import trace
from opensearchpy import OpenSearch

from .types import RetrievalResult


def build_knn_query(
    vector: list[float],
    top_k: int,
    source_includes: list[str] | None = None,
) -> dict:
    query: dict = {
        "size": top_k,
        "query": {
            "knn": {
                "embedding": {
                    "vector": vector,
                    "k": top_k,
                }
            }
        },
    }
    if source_includes:
        query["_source"] = source_includes
    return query


def retrieve_knn(
    client: OpenSearch,
    index_name: str,
    vector: list[float],
    top_k: int,
) -> list[RetrievalResult]:
    tracer = trace.get_tracer("opscopilot_rag")
    with tracer.start_as_current_span("rag.opensearch.search") as span:
        span.set_attribute("index", index_name)
        span.set_attribute("top_k", top_k)
        response = client.search(index=index_name, body=build_knn_query(vector, top_k))
        hits = response.get("hits", {}).get("hits", [])
        results: list[RetrievalResult] = []
        for hit in hits:
            source = hit.get("_source", {})
            results.append(
                RetrievalResult(
                    document_id=source.get("document_id", ""),
                    chunk_id=source.get("chunk_id", ""),
                    chunk_index=source.get("chunk_index", 0),
                    source=source.get("source", ""),
                    text=source.get("text", ""),
                    metadata=source.get("metadata", {}),
                    score=float(hit.get("_score", 0.0)),
                )
            )
        span.set_attribute("retrieved_chunks", len(results))
        return results
