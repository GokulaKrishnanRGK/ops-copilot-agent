from .types import LlmError, LlmOutput, LlmResponse


def normalize_output_text(text: str) -> LlmOutput:
    return LlmOutput(type="text", text=text, json=None)


def normalize_output_json(payload: dict) -> LlmOutput:
    return LlmOutput(type="json", text=None, json=payload)


def normalize_error(error_type: str, message: str) -> LlmError:
    if error_type not in {
        "budget_exceeded",
        "timeout",
        "provider_error",
        "invalid_request",
        "unknown_error",
    }:
        error_type = "unknown_error"
    return LlmError(error_type=error_type, message=message)


def normalize_response(
    output: LlmOutput,
    tokens_input: int,
    tokens_output: int,
    cost_usd: float,
    latency_ms: int,
    provider_metadata: dict,
    error: LlmError | None,
) -> LlmResponse:
    return LlmResponse(
        output=output,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        provider_metadata=provider_metadata,
        error=error,
    )
