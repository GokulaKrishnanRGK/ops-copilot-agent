import pytest

from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer, BudgetState
from opscopilot_llm_gateway.gateway import run_embedding_call
from opscopilot_llm_gateway.types import EmbeddingRequest, EmbeddingResponse, LlmTags


class FakeEmbeddingProvider:
    def __init__(self, vectors, tokens_input, cost_usd=0.0):
        self._vectors = vectors
        self._tokens_input = tokens_input
        self._cost_usd = cost_usd

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        return EmbeddingResponse(
            vectors=self._vectors,
            tokens_input=self._tokens_input,
            cost_usd=self._cost_usd,
            latency_ms=5,
            provider_metadata={"model": request.model_id},
            error=None,
        )


def _request():
    return EmbeddingRequest(
        model_id="text-embedding-3-small",
        texts=["hello"],
        idempotency_key="id",
        tags=LlmTags(session_id="s", agent_run_id="r", agent_node="n"),
    )


def test_run_embedding_call_records_costs():
    provider = FakeEmbeddingProvider(vectors=[[0.1, 0.2]], tokens_input=2000, cost_usd=0.04)
    ledger = CostLedger()
    budget = BudgetEnforcer(BudgetState(max_usd=1.0, total_usd=0.0))

    response = run_embedding_call(provider, _request(), budget, ledger)

    assert response.vectors == [[0.1, 0.2]]
    records = ledger.records()
    assert len(records) == 1
    assert records[0].tokens_input == 2000
    assert records[0].cost_usd == 0.04
    assert budget.state().total_usd == 0.04


def test_run_embedding_call_budget_exceeded():
    provider = FakeEmbeddingProvider(vectors=[[0.1]], tokens_input=1000, cost_usd=1.0)
    ledger = CostLedger()
    budget = BudgetEnforcer(BudgetState(max_usd=0.0001, total_usd=0.0))

    with pytest.raises(RuntimeError, match="budget_exceeded"):
        run_embedding_call(provider, _request(), budget, ledger)
