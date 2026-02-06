from opscopilot_rag.citations import build_citations
from opscopilot_rag.types import RetrievalResult


def test_build_citations_maps_fields():
    results = [
        RetrievalResult(
            document_id="doc",
            chunk_id="doc::chunk-0",
            chunk_index=0,
            source="doc",
            text="text",
            metadata={"source": "doc"},
            score=0.42,
        )
    ]
    citations = build_citations(results)
    assert citations[0].chunk_id == "doc::chunk-0"
    assert citations[0].score == 0.42
