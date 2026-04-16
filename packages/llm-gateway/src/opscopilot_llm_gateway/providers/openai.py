from __future__ import annotations

import os
import time

import litellm

from opscopilot_llm_gateway.types import EmbeddingRequest, EmbeddingResponse


def _read_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is required")
    return key


class OpenAIEmbeddingProvider:
    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        _read_api_key()
        start = time.monotonic()
        response = litellm.embedding(
            model=request.model_id,
            input=request.texts,
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        vectors = [item["embedding"] for item in response.data]
        usage = getattr(response, "usage", None)
        tokens_input = getattr(usage, "total_tokens", 0) or 0
        try:
            cost_usd = float(response._hidden_params.get("response_cost") or 0.0)
        except Exception:
            cost_usd = 0.0
        return EmbeddingResponse(
            vectors=vectors,
            tokens_input=tokens_input,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            provider_metadata={"model": request.model_id},
            error=None,
        )
