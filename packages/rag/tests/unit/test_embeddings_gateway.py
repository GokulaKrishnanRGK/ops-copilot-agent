from pathlib import Path

from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer, BudgetState
from opscopilot_llm_gateway.types import EmbeddingRequest, EmbeddingResponse

from opscopilot_rag.embeddings import OpenAIEmbeddingAdapter
from opscopilot_rag.types import EmbeddingRequest as RagEmbeddingRequest


class FakeEmbeddingProvider:
    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        return EmbeddingResponse(
            vectors=[[0.1, 0.2]],
            tokens_input=10,
            cost_usd=0.0,
            latency_ms=1,
            provider_metadata={"model": request.model_id},
            error=None,
        )


def test_openai_embedding_adapter_uses_gateway():
    repo_root = Path(__file__).resolve().parents[3]
    cost_table_path = repo_root / "llm-gateway/src/opscopilot_llm_gateway/costs.json"

    adapter = OpenAIEmbeddingAdapter(
        provider=FakeEmbeddingProvider(),
        model="text-embedding-3-small",
        cost_table_path=str(cost_table_path),
        budget=BudgetEnforcer(BudgetState(max_usd=1.0, total_usd=0.0)),
        ledger=CostLedger(),
    )
    result = adapter.embed(RagEmbeddingRequest(texts=["hello"]))
    assert result.vectors
    assert result.dimensions == 2
