import pytest

from opscopilot_rag.embeddings import BedrockEmbeddingAdapter
from opscopilot_rag.opensearch_client import OpenSearchClient
from opscopilot_rag.retrieval import retrieve_knn
from opscopilot_rag.types import EmbeddingRequest


def _missing_env() -> list[str]:
    import os
    return [name for name in ["OPENSEARCH_URL", "OPENSEARCH_INDEX", "BEDROCK_REGION", "BEDROCK_EMBEDDING_MODEL_ID"] if not os.getenv(name)]


@pytest.mark.integration
def test_rag_ingested_docs_retrieval():
    missing = _missing_env()
    if missing:
        pytest.skip("missing env: " + ", ".join(missing))

    client = OpenSearchClient()
    config = client.config
    adapter = BedrockEmbeddingAdapter()

    query_embedding = adapter.embed(EmbeddingRequest(texts=["k8s.get_pod_logs"]))
    results = retrieve_knn(client.client, config.index, query_embedding.vectors[0], top_k=3)
    assert results
    sources = [result.source for result in results]
    assert any("tools-reference" in source for source in sources)
