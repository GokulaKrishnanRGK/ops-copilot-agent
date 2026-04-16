from __future__ import annotations

import os

from opscopilot_llm_gateway.providers.bedrock_embeddings import (
    BedrockEmbeddingProvider,
    read_bedrock_embedding_model_id,
)
from opscopilot_llm_gateway.providers.openai import OpenAIEmbeddingProvider


def _read_provider() -> str:
    return os.getenv("LLM_EMBEDDING_PROVIDER", "openai")


def build_embedding_provider():
    provider = _read_provider().lower()
    if provider == "openai":
        return OpenAIEmbeddingProvider()
    if provider == "bedrock":
        return BedrockEmbeddingProvider()
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
