from __future__ import annotations

import os
import uuid

from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer, BudgetState
from opscopilot_llm_gateway.costs import load_cost_table
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider
from opscopilot_llm_gateway.types import (
    LlmMessage,
    LlmRequest,
    LlmResponseFormat,
    LlmTags,
)

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


def _response_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
        },
        "required": ["answer"],
    }


def _tool_summary(tool_results: list) -> str:
    lines = []
    for result in tool_results:
        tool_name = getattr(result, "tool_name", None)
        tool_result = getattr(result, "result", None)
        if tool_name is None and isinstance(result, dict):
            tool_name = result.get("tool_name")
            tool_result = result.get("result")
        lines.append(f"tool={tool_name} result={tool_result}")
    return "\n".join(lines)


class AnswerSynthesizer(LlmNodeBase):
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
    ) -> "AnswerSynthesizer":
        model_id = _read_env("LLM_MODEL_ID")
        cost_table_path = _read_env("LLM_COST_TABLE_PATH")
        cost_table = load_cost_table(cost_table_path)
        budget = BudgetEnforcer(BudgetState(max_usd=_read_budget(), total_usd=0.0))
        ledger = CostLedger()
        return AnswerSynthesizer(provider, model_id, cost_table, budget, ledger, recorder=recorder)

    def synthesize(
        self,
        prompt: str,
        tool_results: list,
        rag_context: str | None = None,
        recorder: AgentRunRecorder | None = None,
    ) -> str:
        system_prompt = "Return a concise answer grounded only in tool results."
        context_block = f"\n\nContext:\n{rag_context}" if rag_context else ""
        user_content = (
            f"Prompt: {prompt}{context_block}\n\nTool results:\n{_tool_summary(tool_results)}"
        )
        request = LlmRequest(
            model_id=self._model_id,
            messages=[
                LlmMessage(role="system", content=system_prompt),
                LlmMessage(role="user", content=user_content),
            ],
            response_format=LlmResponseFormat(type="json_schema", schema=_response_schema()),
            temperature=0.0,
            max_tokens=256,
            idempotency_key=str(uuid.uuid4()),
            tags=LlmTags(session_id="answer", agent_run_id="answer", agent_node="answer"),
        )
        response = self._call(
            request=request,
            agent_node="answer",
            recorder=recorder or self._recorder,
        )
        if response.error:
            raise RuntimeError(response.error.message)
        payload = response.output.json or {}
        answer = payload.get("answer")
        if not answer:
            raise RuntimeError("answer missing")
        return answer
