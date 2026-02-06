from dataclasses import dataclass
from typing import Any, Literal


Role = Literal["system", "user", "assistant"]
ResponseType = Literal["text", "json_schema"]
OutputType = Literal["text", "json"]


@dataclass(frozen=True)
class LlmMessage:
    role: Role
    content: str


@dataclass(frozen=True)
class LlmResponseFormat:
    type: ResponseType
    schema: dict | None


@dataclass(frozen=True)
class LlmTags:
    session_id: str
    agent_run_id: str
    agent_node: str


@dataclass(frozen=True)
class LlmRequest:
    model_id: str
    messages: list[LlmMessage]
    response_format: LlmResponseFormat
    temperature: float
    max_tokens: int
    idempotency_key: str
    tags: LlmTags


@dataclass(frozen=True)
class LlmOutput:
    type: OutputType
    text: str | None
    json: dict | None


@dataclass(frozen=True)
class LlmError:
    error_type: Literal[
        "budget_exceeded",
        "timeout",
        "provider_error",
        "invalid_request",
        "unknown_error",
    ]
    message: str


@dataclass(frozen=True)
class LlmResponse:
    output: LlmOutput
    tokens_input: int
    tokens_output: int
    cost_usd: float
    latency_ms: int
    provider_metadata: dict[str, Any]
    error: LlmError | None


@dataclass(frozen=True)
class EmbeddingRequest:
    model_id: str
    texts: list[str]
    idempotency_key: str
    tags: LlmTags


@dataclass(frozen=True)
class EmbeddingResponse:
    vectors: list[list[float]]
    tokens_input: int
    cost_usd: float
    latency_ms: int
    provider_metadata: dict[str, Any]
    error: LlmError | None
