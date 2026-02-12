import os
import time
import uuid

import pytest

from opscopilot_rag.chunking import chunk_text
from opscopilot_rag.embeddings import OpenAIEmbeddingAdapter
from opscopilot_rag.indexing import build_index_documents, bulk_upsert_chunks
from opscopilot_rag.opensearch_client import OpenSearchClient, ensure_index
from opscopilot_rag.retrieval import retrieve_knn
from opscopilot_rag.types import EmbeddingRequest, OpenSearchConfig


def _embedding_provider() -> str:
    return os.getenv("LLM_EMBEDDING_PROVIDER", "openai").lower()


def _missing_env() -> list[str]:
    required = ["OPENSEARCH_URL"]
    provider = _embedding_provider()
    if provider == "openai":
        required += ["OPENAI_API_KEY", "OPENAI_EMBEDDING_MODEL"]
    if provider == "bedrock":
        required += ["BEDROCK_REGION", "BEDROCK_EMBEDDING_MODEL_ID"]
    return [name for name in required if not os.getenv(name)]


@pytest.mark.integration
def test_opensearch_end_to_end_retrieval():
    missing = _missing_env()
    if missing:
        pytest.skip("missing env: " + ", ".join(missing))

    index_name = f"opscopilot-rag-test-{uuid.uuid4().hex}"
    base_client = OpenSearchClient()
    base_config = base_client.config
    config = OpenSearchConfig(
        url=base_config.url,
        index=index_name,
        username=base_config.username,
        password=base_config.password,
        verify_certs=base_config.verify_certs,
    )
    client = OpenSearchClient(config).client
    adapter = OpenAIEmbeddingAdapter()

    try:
        chunks = chunk_text("doc", "hello world from opscopilot", chunk_size=12, chunk_overlap=2)
        embeddings = adapter.embed(EmbeddingRequest(texts=[chunk.text for chunk in chunks]))
        ensure_index(client, index_name, embeddings.dimensions)
        documents = build_index_documents(chunks, embeddings)
        assert bulk_upsert_chunks(client, index_name, documents) == len(documents)
        time.sleep(2)

        query_embedding = adapter.embed(EmbeddingRequest(texts=["hello world"]))
        results = retrieve_knn(client, index_name, query_embedding.vectors[0], top_k=1)
        assert results
        assert results[0].chunk_id.startswith("doc::chunk-")
    finally:
        client.indices.delete(index=index_name, ignore=[404])
