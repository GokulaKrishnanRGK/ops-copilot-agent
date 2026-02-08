from __future__ import annotations

import os

from opscopilot_llm_gateway.providers.bedrock_embeddings import (
    BedrockEmbeddingProvider,
    build_bedrock_client,
    read_bedrock_embedding_model_id,
)
from opscopilot_llm_gateway.providers.openai import OpenAIEmbeddingProvider, build_openai_client


def _read_provider() -> str:
    return os.getenv("LLM_EMBEDDING_PROVIDER", "openai")


def build_embedding_provider(client=None):
    provider = _read_provider().lower()
    if provider == "openai":
        return OpenAIEmbeddingProvider(client=client or build_openai_client())
    if provider == "bedrock":
        bedrock_client = client or build_bedrock_client()
        return BedrockEmbeddingProvider(client=bedrock_client)
    raise RuntimeError("unknown_embedding_provider")


def read_embedding_model_id() -> str:
    provider = _read_provider().lower()
    if provider == "openai":
        model = os.getenv("OPENAI_EMBEDDING_MODEL")
        if not model:
            raise RuntimeError("OPENAI_EMBEDDING_MODEL is required")
        return model
    if provider == "bedrock":
        return read_bedrock_embedding_model_id()
    raise RuntimeError("unknown_embedding_provider")
