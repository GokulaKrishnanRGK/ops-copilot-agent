import pytest

from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer, BudgetState
from opscopilot_llm_gateway.costs import CostEntry
from opscopilot_llm_gateway.gateway import run_gateway_call
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider, BedrockResult
from opscopilot_llm_gateway.types import (
    LlmMessage,
    LlmRequest,
    LlmResponseFormat,
    LlmTags,
)


class FakeClient:
    def __init__(self, result: BedrockResult):
        self._result = result

    def invoke(self, request):
        return self._result


def _request():
    return LlmRequest(
        model_id="m1",
        messages=[LlmMessage(role="user", content="hi")],
        response_format=LlmResponseFormat(type="text", schema=None),
        temperature=0.0,
        max_tokens=10,
        idempotency_key="k",
        tags=LlmTags(session_id="s", agent_run_id="r", agent_node="planner"),
    )


def test_gateway_records_cost():
    result = BedrockResult(
        output_text="ok",
        output_json=None,
        tokens_input=1000,
        tokens_output=1000,
        cost_usd=0.0,
        latency_ms=10,
        provider_metadata={},
    )
    provider = BedrockProvider(FakeClient(result))
    table = {"m1": CostEntry(model_id="m1", input_per_1k=0.01, output_per_1k=0.01)}
    budget = BudgetEnforcer(BudgetState(max_usd=1.0, total_usd=0.0))
    ledger = CostLedger()
    resp = run_gateway_call(provider, _request(), table, budget, ledger)
    assert resp.output.text == "ok"
    assert len(ledger.records()) == 1


def test_gateway_budget_exceeded():
    result = BedrockResult(
        output_text="ok",
        output_json=None,
        tokens_input=1000,
        tokens_output=1000,
        cost_usd=0.0,
        latency_ms=10,
        provider_metadata={},
    )
    provider = BedrockProvider(FakeClient(result))
    table = {"m1": CostEntry(model_id="m1", input_per_1k=1.0, output_per_1k=1.0)}
    budget = BudgetEnforcer(BudgetState(max_usd=0.5, total_usd=0.0))
    ledger = CostLedger()
    with pytest.raises(RuntimeError):
        run_gateway_call(provider, _request(), table, budget, ledger)
