import json
import os
from typing import Any, Callable

from opentelemetry import trace

from opscopilot_llm_gateway.accounting import CostLedger, CostRecord
from opscopilot_llm_gateway.budgets import BudgetEnforcer
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider
from opscopilot_llm_gateway.types import EmbeddingRequest, EmbeddingResponse, LlmRequest, LlmResponse


def _span_safe(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in value)


def _gateway_span_name(agent_node: str) -> str:
    return f"llm.gateway.{_span_safe(agent_node)}"


def _embedding_span_name(agent_node: str) -> str:
    return f"llm.gateway.embedding.{_span_safe(agent_node)}"



def _messages_payload(request: LlmRequest) -> list[dict[str, str]]:
    return [{"role": message.role, "content": message.content} for message in request.messages]


def _output_payload(response: LlmResponse) -> Any:
    if response.output.type == "json":
        return response.output.json
    return response.output.text


def _json_attribute(payload: Any) -> str:
    return json.dumps(payload, default=str)


def _set_generation_attributes(span, request: LlmRequest, response: LlmResponse, cost_usd: float) -> None:
    span.set_attribute("langfuse.observation.type", "generation")
    span.set_attribute("langfuse.observation.model.name", request.model_id)
    span.set_attribute(
        "langfuse.observation.model.parameters",
        _json_attribute({"temperature": request.temperature, "max_tokens": request.max_tokens}),
    )
    span.set_attribute(
        "langfuse.observation.usage_details",
        _json_attribute(
            {
                "input": response.tokens_input,
                "output": response.tokens_output,
                "total": response.tokens_input + response.tokens_output,
            }
        ),
    )
    span.set_attribute("langfuse.observation.cost_details", _json_attribute({"total": cost_usd}))
    if request.prompt_ref is not None:
        span.set_attribute("langfuse.observation.prompt.name", request.prompt_ref.name)
        span.set_attribute(
            "langfuse.observation.prompt.version",
            request.prompt_ref.langfuse_version or request.prompt_ref.version,
        )
        span.set_attribute("prompt.name", request.prompt_ref.name)
        span.set_attribute("prompt.version", request.prompt_ref.version)
        span.set_attribute("prompt.source", request.prompt_ref.source)
    first_token_ms = response.provider_metadata.get("time_to_first_token_ms")
    if first_token_ms is not None:
        span.set_attribute("time_to_first_token_ms", int(first_token_ms))
        span.set_attribute("ai.response.msToFirstChunk", int(first_token_ms))
    span.set_attribute("ai.response.msToFinish", response.latency_ms)
    if response.tokens_output > 0 and response.latency_ms > 0:
        tokens_per_sec = round(response.tokens_output / (response.latency_ms / 1000.0), 2)
        span.set_attribute("ai.response.avgOutputTokensPerSecond", tokens_per_sec)
    if response.finish_reason:
        span.set_attribute("ai.response.finishReason", response.finish_reason)
    span.set_attribute("ai.usage.inputTokens", response.tokens_input)
    span.set_attribute("ai.usage.outputTokens", response.tokens_output)
    if response.cache_read_input_tokens > 0:
        span.set_attribute("ai.usage.inputTokenDetails.cacheReadTokens", response.cache_read_input_tokens)
    span.set_attribute("langfuse.observation.input", _json_attribute(_messages_payload(request)))
    span.set_attribute("langfuse.observation.output", _json_attribute(_output_payload(response)))
    span.set_attribute(
        "langfuse.observation.metadata",
        _json_attribute({
            "agent_node": request.tags.agent_node,
            "agent_run_id": request.tags.agent_run_id,
            "provider": "bedrock",
            "cache_hit": response.cache_hit,
            "latency_ms": response.latency_ms,
        }),
    )
    env = os.getenv("LANGFUSE_ENVIRONMENT")
    if env:
        span.set_attribute("langfuse.environment", env)
    release = os.getenv("LANGFUSE_RELEASE")
    if release:
        span.set_attribute("langfuse.release", release)


def run_gateway_call(
    provider: BedrockProvider,
    request: LlmRequest,
    budget: BudgetEnforcer,
    ledger: CostLedger,
    on_delta: Callable[[str], None] | None = None,
) -> LlmResponse:
    tracer = trace.get_tracer("opscopilot_llm_gateway")
    with tracer.start_as_current_span(_gateway_span_name(request.tags.agent_node)) as span:
        span.set_attribute("provider", "bedrock")
        if on_delta is None:
            response = provider.invoke(request)
        else:
            response = provider.invoke_stream(request, on_delta)
        cost_usd = response.cost_usd
        span.set_attribute("gen_ai.request.model", request.model_id)
        span.set_attribute("gen_ai.usage.input_tokens", response.tokens_input)
        span.set_attribute("gen_ai.usage.output_tokens", response.tokens_output)
        span.set_attribute("agent_node", request.tags.agent_node)
        span.set_attribute("cost_usd", cost_usd)
        span.set_attribute("session.id", request.tags.session_id)
        span.set_attribute("agent_run_id", request.tags.agent_run_id)
        span.set_attribute("latency_ms", response.latency_ms)
        _set_generation_attributes(span, request, response, cost_usd)
        if not budget.can_spend(cost_usd):
            raise RuntimeError("budget_exceeded")
        budget.record_spend(cost_usd)
        ledger.record(
            CostRecord(
                session_id=request.tags.session_id,
                agent_run_id=request.tags.agent_run_id,
                agent_node=request.tags.agent_node,
                model_id=request.model_id,
                tokens_input=response.tokens_input,
                tokens_output=response.tokens_output,
                cost_usd=cost_usd,
            )
        )
        return response


def run_embedding_call(
    provider,
    request: EmbeddingRequest,
    budget: BudgetEnforcer,
    ledger: CostLedger,
) -> EmbeddingResponse:
    tracer = trace.get_tracer("opscopilot_llm_gateway")
    with tracer.start_as_current_span(_embedding_span_name(request.tags.agent_node)) as span:
        span.set_attribute("langfuse.observation.type", "generation")
        span.set_attribute("provider", "embedding")
        response = provider.embed(request)
        cost_usd = response.cost_usd
        span.set_attribute("gen_ai.request.model", request.model_id)
        span.set_attribute("gen_ai.usage.input_tokens", response.tokens_input)
        span.set_attribute("gen_ai.usage.output_tokens", 0)
        span.set_attribute("agent_node", request.tags.agent_node)
        span.set_attribute("cost_usd", cost_usd)
        span.set_attribute("session.id", request.tags.session_id)
        span.set_attribute("agent_run_id", request.tags.agent_run_id)
        span.set_attribute("latency_ms", response.latency_ms)
        if not budget.can_spend(cost_usd):
            raise RuntimeError("budget_exceeded")
        budget.record_spend(cost_usd)
        ledger.record(
            CostRecord(
                session_id=request.tags.session_id,
                agent_run_id=request.tags.agent_run_id,
                agent_node=request.tags.agent_node,
                model_id=request.model_id,
                tokens_input=response.tokens_input,
                tokens_output=0,
                cost_usd=cost_usd,
            )
        )
        return EmbeddingResponse(
            vectors=response.vectors,
            tokens_input=response.tokens_input,
            cost_usd=cost_usd,
            latency_ms=response.latency_ms,
            provider_metadata=response.provider_metadata,
            error=response.error,
        )
