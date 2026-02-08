from __future__ import annotations

import os
import time
from dataclasses import dataclass

from openai import OpenAI

from opscopilot_llm_gateway.types import EmbeddingRequest, EmbeddingResponse


def build_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required")
    return OpenAI(api_key=api_key)


@dataclass(frozen=True)
class OpenAIEmbeddingProvider:
    client: OpenAI

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        start = time.monotonic()
        response = self.client.embeddings.create(
            model=request.model_id,
            input=request.texts,
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        vectors = [item.embedding for item in response.data]
        tokens_input = response.usage.total_tokens if response.usage else 0
        return EmbeddingResponse(
            vectors=vectors,
            tokens_input=tokens_input,
            cost_usd=0.0,
            latency_ms=latency_ms,
            provider_metadata={"model": request.model_id},
            error=None,
        )
