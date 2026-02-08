from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer, BudgetState
from opscopilot_llm_gateway.gateway import run_embedding_call
from opscopilot_llm_gateway.types import EmbeddingRequest, EmbeddingResponse, LlmTags


class FakeEmbeddingProvider:
    def __init__(self, vectors, tokens_input):
        self._vectors = vectors
        self._tokens_input = tokens_input

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        return EmbeddingResponse(
            vectors=self._vectors,
            tokens_input=self._tokens_input,
            cost_usd=0.0,
            latency_ms=5,
            provider_metadata={"model": request.model_id},
            error=None,
        )


def test_run_embedding_call_records_costs():
    provider = FakeEmbeddingProvider(vectors=[[0.1, 0.2]], tokens_input=2000)
    request = EmbeddingRequest(
        model_id="text-embedding-3-small",
        texts=["hello"],
        idempotency_key="id",
        tags=LlmTags(session_id="s", agent_run_id="r", agent_node="n"),
    )
    cost_table = {
        "text-embedding-3-small": type(
            "Cost",
            (),
            {"model_id": "text-embedding-3-small", "input_per_1k": 0.00002, "output_per_1k": 0.0},
        )()
    }
    ledger = CostLedger()
    budget = BudgetEnforcer(BudgetState(max_usd=1.0, total_usd=0.0))

    response = run_embedding_call(provider, request, cost_table, budget, ledger)

    assert response.vectors == [[0.1, 0.2]]
    records = ledger.records()
    assert len(records) == 1
    assert records[0].tokens_input == 2000


def test_run_embedding_call_budget_exceeded():
    provider = FakeEmbeddingProvider(vectors=[[0.1]], tokens_input=1000000)
    request = EmbeddingRequest(
        model_id="text-embedding-3-small",
        texts=["hello"],
        idempotency_key="id",
        tags=LlmTags(session_id="s", agent_run_id="r", agent_node="n"),
    )
    cost_table = {
        "text-embedding-3-small": type(
            "Cost",
            (),
            {"model_id": "text-embedding-3-small", "input_per_1k": 0.01, "output_per_1k": 0.0},
        )()
    }
    ledger = CostLedger()
    budget = BudgetEnforcer(BudgetState(max_usd=0.0001, total_usd=0.0))

    try:
        run_embedding_call(provider, request, cost_table, budget, ledger)
    except RuntimeError as exc:
        assert "budget_exceeded" in str(exc)
    else:
        raise AssertionError("expected budget_exceeded")
