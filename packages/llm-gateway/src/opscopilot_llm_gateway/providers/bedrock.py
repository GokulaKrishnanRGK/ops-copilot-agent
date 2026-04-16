from __future__ import annotations

import json
import time
from typing import Callable

import litellm

from opscopilot_llm_gateway.types import LlmOutput, LlmRequest, LlmResponse


def _prefixed(model_id: str) -> str:
    if model_id.startswith("bedrock/"):
        return model_id
    return f"bedrock/{model_id}"


def _build_messages(request: LlmRequest) -> list[dict]:
    msgs = [{"role": m.role, "content": m.content} for m in request.messages]
    if request.response_format.type == "json_schema" and request.response_format.schema:
        schema_str = json.dumps(request.response_format.schema)
        for i in range(len(msgs) - 1, -1, -1):
            if msgs[i]["role"] == "user":
                msgs[i] = {**msgs[i], "content": f"{msgs[i]['content']}\n\nReturn JSON only that matches this schema: {schema_str}"}
                break
    return msgs


def _parse_json(text: str) -> dict | None:
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            return json.loads(text[start : end + 1])
        except Exception:
            return None


def _make_output(text: str, is_json: bool) -> LlmOutput:
    if is_json:
        parsed = _parse_json(text)
        if parsed is not None:
            return LlmOutput(type="json", text=None, json=parsed)
    return LlmOutput(type="text", text=text, json=None)


def _extract_cost(response) -> float:
    try:
        return float(response._hidden_params.get("response_cost") or 0.0)
    except Exception:
        return 0.0


class BedrockProvider:
    def invoke(self, request: LlmRequest) -> LlmResponse:
        start = time.monotonic()
        response = litellm.completion(
            model=_prefixed(request.model_id),
            messages=_build_messages(request),
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=False,
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        text = response.choices[0].message.content or ""
        usage = response.usage or {}
        tokens_input = getattr(usage, "prompt_tokens", 0) or 0
        tokens_output = getattr(usage, "completion_tokens", 0) or 0
        return LlmResponse(
            output=_make_output(text, request.response_format.type == "json_schema"),
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_usd=_extract_cost(response),
            latency_ms=latency_ms,
            provider_metadata={"model": request.model_id},
            error=None,
        )

    def invoke_stream(self, request: LlmRequest, on_delta: Callable[[str], None]) -> LlmResponse:
        start = time.monotonic()
        stream = litellm.completion(
            model=_prefixed(request.model_id),
            messages=_build_messages(request),
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=True,
            stream_options={"include_usage": True},
        )
        chunks: list[str] = []
        tokens_input = 0
        tokens_output = 0
        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                chunks.append(delta)
                on_delta(delta)
            usage = getattr(chunk, "usage", None)
            if usage:
                tokens_input = getattr(usage, "prompt_tokens", 0) or 0
                tokens_output = getattr(usage, "completion_tokens", 0) or 0

        latency_ms = int((time.monotonic() - start) * 1000)
        text = "".join(chunks)
        try:
            cost_usd = litellm.completion_cost(
                model=_prefixed(request.model_id),
                prompt_tokens=tokens_input,
                completion_tokens=tokens_output,
            )
        except Exception:
            cost_usd = 0.0
        return LlmResponse(
            output=_make_output(text, request.response_format.type == "json_schema"),
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_usd=float(cost_usd),
            latency_ms=latency_ms,
            provider_metadata={"model": request.model_id},
            error=None,
        )
