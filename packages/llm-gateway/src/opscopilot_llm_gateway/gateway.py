from opscopilot_llm_gateway.accounting import CostLedger, CostRecord
from opscopilot_llm_gateway.budgets import BudgetEnforcer
from opscopilot_llm_gateway.costs import estimate_cost_usd
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider
from opscopilot_llm_gateway.types import LlmRequest, LlmResponse


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
