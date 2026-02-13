from dataclasses import dataclass
import json
import logging
import os
import time
from typing import Any

import boto3

from opscopilot_llm_gateway.normalize import (
    normalize_output_json,
    normalize_output_text,
    normalize_response,
)
from opscopilot_llm_gateway.types import LlmRequest, LlmResponse

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class BedrockResult:
    output_text: str | None
    output_json: dict | None
    tokens_input: int
    tokens_output: int
    cost_usd: float
    latency_ms: int
    provider_metadata: dict[str, Any]


class BedrockProvider:
    def __init__(self, client: Any):
        self._client = client

    def invoke(self, request: LlmRequest) -> LlmResponse:
        raw = self._client.invoke(request)
        output = self._to_output(raw)
        return normalize_response(
            output=output,
            tokens_input=raw.tokens_input,
            tokens_output=raw.tokens_output,
            cost_usd=raw.cost_usd,
            latency_ms=raw.latency_ms,
            provider_metadata=raw.provider_metadata,
            error=None,
        )

    def invoke_stream(self, request: LlmRequest, on_delta) -> LlmResponse:
        raw = self._client.invoke_stream(request, on_delta)
        output = self._to_output(raw)
        return normalize_response(
            output=output,
            tokens_input=raw.tokens_input,
            tokens_output=raw.tokens_output,
            cost_usd=raw.cost_usd,
            latency_ms=raw.latency_ms,
            provider_metadata=raw.provider_metadata,
            error=None,
        )

    def _to_output(self, raw: BedrockResult):
        if raw.output_json is not None:
            return normalize_output_json(raw.output_json)
        return normalize_output_text(raw.output_text or "")


def _read_region() -> str:
    region = os.getenv("BEDROCK_REGION") or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
    if not region:
        raise RuntimeError("BEDROCK_REGION is required")
    return region


def _build_prompt(request: LlmRequest) -> str:
    parts = []
    for message in request.messages:
        parts.append(f"{message.role}: {message.content}")
    prompt = "\n".join(parts)
    if request.response_format.type == "json_schema" and request.response_format.schema:
        schema = json.dumps(request.response_format.schema)
        prompt = f"{prompt}\n\nReturn JSON only that matches this schema: {schema}"
    return prompt


def _parse_json(text: str) -> dict | None:
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        snippet = text[start : end + 1]
        try:
            return json.loads(snippet)
        except Exception:
            return None


@dataclass(frozen=True)
class BedrockClient:
    client: Any

    def invoke(self, request: LlmRequest) -> BedrockResult:
        prompt = _build_prompt(request)
        start = time.monotonic()
        response = self.client.converse(
            modelId=request.model_id,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": prompt}],
                }
            ],
            inferenceConfig={
                "maxTokens": request.max_tokens,
                "temperature": request.temperature,
            },
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        message = response.get("output", {}).get("message", {})
        content = message.get("content", [])
        text = ""
        if content:
            text = content[0].get("text", "")
        output_json = None
        if request.response_format.type == "json_schema":
            output_json = _parse_json(text)
        if os.getenv("LLM_DEBUG", "0") == "1":
            logger.info(
                "bedrock response model=%s text=%s json=%s",
                request.model_id,
                text,
                output_json,
            )
        return BedrockResult(
            output_text=text if output_json is None else None,
            output_json=output_json,
            tokens_input=response.get("usage", {}).get("inputTokens", 0),
            tokens_output=response.get("usage", {}).get("outputTokens", 0),
            cost_usd=0.0,
            latency_ms=latency_ms,
            provider_metadata={"model": request.model_id},
        )

    def invoke_stream(self, request: LlmRequest, on_delta) -> BedrockResult:
        prompt = _build_prompt(request)
        start = time.monotonic()
        response = self.client.converse_stream(
            modelId=request.model_id,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": prompt}],
                }
            ],
            inferenceConfig={
                "maxTokens": request.max_tokens,
                "temperature": request.temperature,
            },
        )
        chunks: list[str] = []
        stream = response.get("stream", [])
        usage = {}
        for event in stream:
            delta = event.get("contentBlockDelta", {}).get("delta", {})
            text_delta = delta.get("text")
            if text_delta:
                chunks.append(text_delta)
                on_delta(text_delta)
            metadata = event.get("metadata", {})
            if metadata.get("usage"):
                usage = metadata.get("usage", {})

        text = "".join(chunks)
        latency_ms = int((time.monotonic() - start) * 1000)
        output_json = None
        if request.response_format.type == "json_schema":
            output_json = _parse_json(text)
        if os.getenv("LLM_DEBUG", "0") == "1":
            logger.info(
                "bedrock stream response model=%s text=%s json=%s",
                request.model_id,
                text,
                output_json,
            )
        return BedrockResult(
            output_text=text if output_json is None else None,
            output_json=output_json,
            tokens_input=usage.get("inputTokens", 0),
            tokens_output=usage.get("outputTokens", 0),
            cost_usd=0.0,
            latency_ms=latency_ms,
            provider_metadata={"model": request.model_id},
        )


def build_bedrock_client() -> BedrockClient:
    profile = os.getenv("AWS_PROFILE")
    region = _read_region()
    if profile:
        session = boto3.Session(profile_name=profile, region_name=region)
        runtime = session.client("bedrock-runtime")
    else:
        runtime = boto3.client("bedrock-runtime", region_name=region)
    return BedrockClient(client=runtime)
