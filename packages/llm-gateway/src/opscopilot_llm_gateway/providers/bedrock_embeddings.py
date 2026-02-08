from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

import boto3

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


@dataclass(frozen=True)
class BedrockEmbeddingClient:
    client: Any

    def invoke_embedding(self, model_id: str, texts: list[str]):
        vectors: list[list[float]] = []
        tokens_input = 0
        for text in texts:
            body = json.dumps({"inputText": text})
            attempts = 0
            while True:
                try:
                    response = self.client.invoke_model(modelId=model_id, body=body)
                    payload = json.loads(response["body"].read().decode("utf-8"))
                    vectors.append(payload.get("embedding", []))
                    break
                except Exception as exc:
                    attempts += 1
                    if attempts >= 5:
                        raise exc
                    time.sleep(2**attempts / 2)
        return BedrockEmbeddingResult(
            vectors=vectors,
            tokens_input=tokens_input,
            cost_usd=0.0,
            provider_metadata={"model": model_id},
        )


@dataclass(frozen=True)
class BedrockEmbeddingResult:
    vectors: list[list[float]]
    tokens_input: int
    cost_usd: float
    provider_metadata: dict[str, Any]


@dataclass(frozen=True)
class BedrockEmbeddingProvider:
    client: BedrockEmbeddingClient

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        start = time.monotonic()
        response = self.client.invoke_embedding(
            model_id=request.model_id,
            texts=request.texts,
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        return EmbeddingResponse(
            vectors=response.vectors,
            tokens_input=response.tokens_input,
            cost_usd=response.cost_usd,
            latency_ms=latency_ms,
            provider_metadata=response.provider_metadata,
            error=None,
        )


def build_bedrock_client() -> BedrockEmbeddingClient:
    profile = os.getenv("AWS_PROFILE")
    region = read_bedrock_region()
    if profile:
        session = boto3.Session(profile_name=profile, region_name=region)
        runtime = session.client("bedrock-runtime")
    else:
        runtime = boto3.client("bedrock-runtime", region_name=region)
    return BedrockEmbeddingClient(client=runtime)
