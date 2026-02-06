from opscopilot_llm_gateway.accounting import CostLedger, CostRecord
from opscopilot_llm_gateway.budgets import BudgetEnforcer
from opscopilot_llm_gateway.costs import estimate_cost_usd
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider
from opscopilot_llm_gateway.providers.openai import OpenAIEmbeddingProvider
from opscopilot_llm_gateway.types import EmbeddingRequest, EmbeddingResponse, LlmRequest, LlmResponse


def run_gateway_call(
    provider: BedrockProvider,
    request: LlmRequest,
    cost_table: dict,
    budget: BudgetEnforcer,
    ledger: CostLedger,
) -> LlmResponse:
    response = provider.invoke(request)
    estimated = estimate_cost_usd(
        cost_table,
        request.model_id,
        response.tokens_input,
        response.tokens_output,
    )
    if not budget.can_spend(estimated):
        raise RuntimeError("budget_exceeded")
    budget.record_spend(estimated)
    ledger.record(
        CostRecord(
            session_id=request.tags.session_id,
            agent_run_id=request.tags.agent_run_id,
            agent_node=request.tags.agent_node,
            model_id=request.model_id,
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            cost_usd=estimated,
        )
    )
    return response


def run_embedding_call(
    provider: OpenAIEmbeddingProvider,
    request: EmbeddingRequest,
    cost_table: dict,
    budget: BudgetEnforcer,
    ledger: CostLedger,
) -> EmbeddingResponse:
    response = provider.embed(request)
    estimated = estimate_cost_usd(
        cost_table,
        request.model_id,
        response.tokens_input,
        0,
    )
    if not budget.can_spend(estimated):
        raise RuntimeError("budget_exceeded")
    budget.record_spend(estimated)
    ledger.record(
        CostRecord(
            session_id=request.tags.session_id,
            agent_run_id=request.tags.agent_run_id,
            agent_node=request.tags.agent_node,
            model_id=request.model_id,
            tokens_input=response.tokens_input,
            tokens_output=0,
            cost_usd=estimated,
        )
    )
    return EmbeddingResponse(
        vectors=response.vectors,
        tokens_input=response.tokens_input,
        cost_usd=estimated,
        latency_ms=response.latency_ms,
        provider_metadata=response.provider_metadata,
        error=response.error,
    )
