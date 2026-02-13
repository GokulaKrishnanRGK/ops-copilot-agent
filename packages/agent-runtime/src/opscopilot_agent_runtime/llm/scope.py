from __future__ import annotations

import json
import os
import uuid
from typing import Callable

from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer, BudgetState
from opscopilot_llm_gateway.costs import load_cost_table
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider
from opscopilot_llm_gateway.types import LlmMessage, LlmRequest, LlmResponseFormat, LlmTags

from opscopilot_agent_runtime.persistence import AgentRunRecorder

from .base import LlmNodeBase


def _read_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _read_budget() -> float:
    value = os.getenv("LLM_MAX_BUDGET_USD", "1.0")
    try:
        return float(value)
    except ValueError as exc:
        raise RuntimeError("LLM_MAX_BUDGET_USD must be a number") from exc


def _scope_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "allowed": {"type": "boolean"},
            "response": {"type": "string"},
        },
        "required": ["allowed", "response"],
    }


class ScopeClassifier(LlmNodeBase):
    def __init__(
        self,
        provider: BedrockProvider,
        model_id: str,
        cost_table: dict,
        budget: BudgetEnforcer,
        ledger: CostLedger,
        recorder: AgentRunRecorder | None = None,
    ) -> None:
        super().__init__(provider, model_id, cost_table, budget, ledger)
        self._recorder = recorder

    @staticmethod
    def from_env(
        provider: BedrockProvider,
        recorder: AgentRunRecorder | None = None,
    ) -> "ScopeClassifier":
        model_id = _read_env("LLM_MODEL_ID")
        cost_table_path = _read_env("LLM_COST_TABLE_PATH")
        cost_table = load_cost_table(cost_table_path)
        budget = BudgetEnforcer(BudgetState(max_usd=_read_budget(), total_usd=0.0))
        ledger = CostLedger()
        return ScopeClassifier(provider, model_id, cost_table, budget, ledger, recorder=recorder)

    def classify(
        self,
        prompt: str,
        tool_names: list[str],
        rag_context: str | None = None,
        recorder: AgentRunRecorder | None = None,
        on_delta: Callable[[str], None] | None = None,
    ) -> dict:
        system_prompt = (
            "You are a strict scope guard for an agent that can answer using tools "
            "or using retrieved knowledge base context when provided. "
            "If the prompt is not about the available tools and no relevant context is provided, "
            "set allowed=false and provide a short response explaining it only handles tool-based "
            "or knowledge-base requests. "
            "Use rag_context only to determine if the topic is in scope. "
            "Do not infer concrete runtime facts or resource names from rag_context. "
            "Keep response generic and capability-focused."
        )
        payload = {"prompt": prompt, "tools": tool_names}
        if rag_context:
            payload["rag_context"] = rag_context
        request = LlmRequest(
            model_id=self._model_id,
            messages=[
                LlmMessage(role="system", content=system_prompt),
                LlmMessage(
                    role="user",
                    content=json.dumps(payload),
                ),
            ],
            response_format=LlmResponseFormat(type="json_schema", schema=_scope_schema()),
            temperature=0.0,
            max_tokens=128,
            idempotency_key=str(uuid.uuid4()),
            tags=LlmTags(session_id="scope", agent_run_id="scope", agent_node="scope"),
        )
        response = self._call(
            request=request,
            agent_node="scope",
            recorder=recorder or self._recorder,
            on_delta=on_delta,
        )
        if response.error:
            raise RuntimeError(response.error.message)
        return response.output.json or {}
