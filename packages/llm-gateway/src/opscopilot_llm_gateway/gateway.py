from typing import Callable

from opentelemetry import trace

from opscopilot_llm_gateway.accounting import CostLedger, CostRecord
from opscopilot_llm_gateway.budgets import BudgetEnforcer
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider
from opscopilot_llm_gateway.types import EmbeddingRequest, EmbeddingResponse, LlmRequest, LlmResponse


def run_gateway_call(
    provider: BedrockProvider,
    request: LlmRequest,
    budget: BudgetEnforcer,
    ledger: CostLedger,
    on_delta: Callable[[str], None] | None = None,
) -> LlmResponse:
    tracer = trace.get_tracer("opscopilot_llm_gateway")
    with tracer.start_as_current_span("llm.gateway.call") as span:
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
        span.set_attribute("session_id", request.tags.session_id)
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
    with tracer.start_as_current_span("llm.gateway.embedding_call") as span:
        span.set_attribute("provider", "embedding")
        response = provider.embed(request)
        cost_usd = response.cost_usd
        span.set_attribute("gen_ai.request.model", request.model_id)
        span.set_attribute("gen_ai.usage.input_tokens", response.tokens_input)
        span.set_attribute("gen_ai.usage.output_tokens", 0)
        span.set_attribute("agent_node", request.tags.agent_node)
        span.set_attribute("cost_usd", cost_usd)
        span.set_attribute("session_id", request.tags.session_id)
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
