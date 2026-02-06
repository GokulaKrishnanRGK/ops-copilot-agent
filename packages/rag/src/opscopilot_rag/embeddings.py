from __future__ import annotations

import os
import uuid

from openai import OpenAI

from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer, BudgetState
from opscopilot_llm_gateway.costs import load_cost_table
from opscopilot_llm_gateway.gateway import run_embedding_call
from opscopilot_llm_gateway.providers.openai import OpenAIEmbeddingProvider
from opscopilot_llm_gateway.types import EmbeddingRequest, EmbeddingResponse, LlmTags

from .types import EmbeddingRequest as RagEmbeddingRequest
from .types import EmbeddingResult


def _read_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _read_budget() -> float:
    value = os.getenv("RAG_EMBEDDING_MAX_BUDGET_USD", "1.0")
    try:
        return float(value)
    except ValueError as exc:
        raise RuntimeError("RAG_EMBEDDING_MAX_BUDGET_USD must be a number") from exc


def build_openai_client() -> OpenAI:
    api_key = _read_env("OPENAI_API_KEY")
    return OpenAI(api_key=api_key)


def read_openai_model() -> str:
    return _read_env("OPENAI_EMBEDDING_MODEL")


def read_cost_table_path() -> str:
    return _read_env("LLM_COST_TABLE_PATH")


class EmbeddingAdapter:
    def embed(self, request: RagEmbeddingRequest) -> EmbeddingResult:
        raise NotImplementedError("embedding adapter is not configured")


class OpenAIEmbeddingAdapter(EmbeddingAdapter):
    def __init__(
        self,
        client: OpenAI | None = None,
        model: str | None = None,
        cost_table_path: str | None = None,
        budget: BudgetEnforcer | None = None,
        ledger: CostLedger | None = None,
    ) -> None:
        self.client = client or build_openai_client()
        self.model = model or read_openai_model()
        self.cost_table = load_cost_table(cost_table_path or read_cost_table_path())
        self.budget = budget or BudgetEnforcer(
            BudgetState(max_usd=_read_budget(), total_usd=0.0)
        )
        self.ledger = ledger or CostLedger()

    def embed(self, request: RagEmbeddingRequest) -> EmbeddingResult:
        tags = LlmTags(session_id="rag", agent_run_id="rag", agent_node="rag")
        gateway_request = EmbeddingRequest(
            model_id=self.model,
            texts=request.texts,
            idempotency_key=str(uuid.uuid4()),
            tags=tags,
        )
        provider = OpenAIEmbeddingProvider(client=self.client)
        response: EmbeddingResponse = run_embedding_call(
            provider=provider,
            request=gateway_request,
            cost_table=self.cost_table,
            budget=self.budget,
            ledger=self.ledger,
        )
        dimensions = len(response.vectors[0]) if response.vectors else 0
        return EmbeddingResult(
            vectors=response.vectors,
            model_id=self.model,
            dimensions=dimensions,
        )
