from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer, BudgetState

from opscopilot_rag.embeddings import OpenAIEmbeddingAdapter
from opscopilot_rag.types import EmbeddingRequest


class FakeOpenAIClient:
    class _Embeddings:
        def create(self, model, input):
            class _Usage:
                total_tokens = 10

            class _Item:
                def __init__(self, embedding):
                    self.embedding = embedding

            class _Response:
                def __init__(self):
                    self.data = [_Item([0.1, 0.2])]
                    self.usage = _Usage()

            return _Response()

    def __init__(self):
        self.embeddings = self._Embeddings()


def test_openai_embedding_adapter_uses_gateway():
    adapter = OpenAIEmbeddingAdapter(
        client=FakeOpenAIClient(),
        model="text-embedding-3-small",
        budget=BudgetEnforcer(BudgetState(max_usd=1.0, total_usd=0.0)),
        ledger=CostLedger(),
    )
    result = adapter.embed(EmbeddingRequest(texts=["hello"]))
    assert result.vectors
    assert result.dimensions == 2
