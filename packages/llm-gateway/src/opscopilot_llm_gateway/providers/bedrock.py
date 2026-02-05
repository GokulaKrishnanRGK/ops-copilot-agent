from dataclasses import dataclass
from typing import Any

from opscopilot_llm_gateway.normalize import (
    normalize_output_json,
    normalize_output_text,
    normalize_response,
)
from opscopilot_llm_gateway.types import LlmRequest, LlmResponse


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

    def _to_output(self, raw: BedrockResult):
        if raw.output_json is not None:
            return normalize_output_json(raw.output_json)
        return normalize_output_text(raw.output_text or "")
