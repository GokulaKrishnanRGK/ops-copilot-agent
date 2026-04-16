from unittest.mock import MagicMock, patch

import pytest

from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer, BudgetState
from opscopilot_llm_gateway.gateway import run_gateway_call
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider
from opscopilot_llm_gateway.types import (
    LlmMessage,
    LlmOutput,
    LlmRequest,
    LlmResponse,
    LlmResponseFormat,
    LlmTags,
)


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


def _fake_provider(cost_usd=0.02):
    provider = MagicMock(spec=BedrockProvider)
    provider.invoke.return_value = LlmResponse(
        output=LlmOutput(type="text", text="ok", json=None),
        tokens_input=1000,
        tokens_output=1000,
        cost_usd=cost_usd,
        latency_ms=10,
        provider_metadata={},
        error=None,
    )
    return provider


def test_gateway_records_cost():
    provider = _fake_provider(cost_usd=0.02)
    budget = BudgetEnforcer(BudgetState(max_usd=1.0, total_usd=0.0))
    ledger = CostLedger()

    resp = run_gateway_call(provider, _request(), budget, ledger)

    assert resp.output.text == "ok"
    records = ledger.records()
    assert len(records) == 1
    assert records[0].cost_usd == 0.02
    assert budget.state().total_usd == 0.02


def test_gateway_budget_exceeded():
    provider = _fake_provider(cost_usd=2.0)
    budget = BudgetEnforcer(BudgetState(max_usd=0.5, total_usd=0.0))
    ledger = CostLedger()

    with pytest.raises(RuntimeError, match="budget_exceeded"):
        run_gateway_call(provider, _request(), budget, ledger)


def test_gateway_streaming_routes_through_gateway():
    provider = MagicMock(spec=BedrockProvider)
    provider.invoke_stream.return_value = LlmResponse(
        output=LlmOutput(type="text", text="streamed", json=None),
        tokens_input=5,
        tokens_output=5,
        cost_usd=0.001,
        latency_ms=50,
        provider_metadata={},
        error=None,
    )
    budget = BudgetEnforcer(BudgetState(max_usd=1.0, total_usd=0.0))
    ledger = CostLedger()
    deltas: list[str] = []

    resp = run_gateway_call(provider, _request(), budget, ledger, on_delta=deltas.append)

    provider.invoke_stream.assert_called_once()
    provider.invoke.assert_not_called()
    assert resp.output.text == "streamed"
    assert ledger.records()[0].cost_usd == 0.001
