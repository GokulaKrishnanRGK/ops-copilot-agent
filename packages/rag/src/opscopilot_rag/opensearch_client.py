from __future__ import annotations

import os
import logging

from opensearchpy import OpenSearch

from .types import OpenSearchConfig

logger = logging.getLogger(__name__)


def _read_env(name: str, fallback: str | None = None) -> str | None:
    value = os.getenv(name)
    if value:
        return value
    return fallback


def _read_required_env(name: str) -> str:
    value = _read_env(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _parse_bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def opensearch_config_from_env() -> OpenSearchConfig:
    return OpenSearchConfig(
        url=_read_required_env("OPENSEARCH_URL"),
        index=_read_required_env("OPENSEARCH_INDEX"),
        username=_read_env("OPENSEARCH_USERNAME"),
        password=_read_env("OPENSEARCH_PASSWORD"),
        verify_certs=_parse_bool(_read_env("OPENSEARCH_VERIFY_CERTS", "false")),
    )


class OpenSearchClient:
    def __init__(self, config: OpenSearchConfig | None = None) -> None:
        self.config = config or opensearch_config_from_env()
        logger.info(
            "Initializing OpenSearch client for index=%s url=%s verify_certs=%s",
            self.config.index,
            self.config.url,
            self.config.verify_certs,
        )
        http_auth = None
        if self.config.username and self.config.password:
            http_auth = (self.config.username, self.config.password)
        self.client = OpenSearch(
            hosts=[self.config.url],
            http_auth=http_auth,
            use_ssl=self.config.url.startswith("https"),
            verify_certs=self.config.verify_certs,
            ssl_assert_hostname=self.config.verify_certs,
            ssl_show_warn=self.config.verify_certs,
        )

    def ensure_index(self, dimensions: int) -> None:
        ensure_index(self.client, self.config.index, dimensions)


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
        logger.debug("OpenSearch index already exists index=%s", index_name)
        return
    logger.info(
        "Creating OpenSearch index index=%s dimensions=%d",
        index_name,
        dimensions,
    )
    client.indices.create(index=index_name, body=build_index_body(dimensions))
