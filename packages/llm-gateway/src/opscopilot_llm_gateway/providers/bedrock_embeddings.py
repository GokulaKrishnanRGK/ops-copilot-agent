from __future__ import annotations

import os
import time

import litellm

from opscopilot_llm_gateway.types import EmbeddingRequest, EmbeddingResponse


def read_bedrock_region() -> str:
    region = os.getenv("BEDROCK_REGION") or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
    if not region:
        raise RuntimeError("BEDROCK_REGION is required")
    return region


def read_bedrock_embedding_model_id() -> str:
    model_id = os.getenv("BEDROCK_EMBEDDING_MODEL_ID")
    if not model_id:
        raise RuntimeError("BEDROCK_EMBEDDING_MODEL_ID is required")
    return model_id


def _prefixed(model_id: str) -> str:
    if model_id.startswith("bedrock/"):
        return model_id
    return f"bedrock/{model_id}"


class BedrockEmbeddingProvider:
    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        start = time.monotonic()
        response = litellm.embedding(
            model=_prefixed(request.model_id),
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
