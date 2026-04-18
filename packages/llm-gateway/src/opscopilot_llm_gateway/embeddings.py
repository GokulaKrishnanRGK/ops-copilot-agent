from __future__ import annotations

from opscopilot_llm_gateway.providers.bedrock_embeddings import (
    BedrockEmbeddingProvider,
    read_bedrock_embedding_model_id,
)


def build_embedding_provider() -> BedrockEmbeddingProvider:
    return BedrockEmbeddingProvider()


def read_embedding_model_id() -> str:
    return read_bedrock_embedding_model_id()
