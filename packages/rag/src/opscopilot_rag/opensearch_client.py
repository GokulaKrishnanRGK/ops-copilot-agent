from __future__ import annotations

from opensearchpy import OpenSearch

from .types import OpenSearchConfig


def create_opensearch_client(config: OpenSearchConfig) -> OpenSearch:
    http_auth = None
    if config.username and config.password:
        http_auth = (config.username, config.password)
    return OpenSearch(
        hosts=[config.url],
        http_auth=http_auth,
        use_ssl=config.url.startswith("https"),
        verify_certs=config.verify_certs,
        ssl_assert_hostname=config.verify_certs,
        ssl_show_warn=config.verify_certs,
    )


def build_index_body(dimensions: int) -> dict:
    return {
        "settings": {"index.knn": True},
        "mappings": {
            "properties": {
                "document_id": {"type": "keyword"},
                "chunk_id": {"type": "keyword"},
                "chunk_index": {"type": "integer"},
                "source": {"type": "keyword"},
                "text": {"type": "text"},
                "metadata": {"type": "object"},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": dimensions,
                },
            }
        },
    }


def ensure_index(client: OpenSearch, index_name: str, dimensions: int) -> None:
    if client.indices.exists(index=index_name):
        return
    client.indices.create(index=index_name, body=build_index_body(dimensions))
