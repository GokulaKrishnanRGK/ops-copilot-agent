from __future__ import annotations

import json
import os
import uuid

from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer, BudgetState
from opscopilot_llm_gateway.costs import load_cost_table
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider
from opscopilot_llm_gateway.types import LlmMessage, LlmRequest, LlmResponseFormat, LlmTags

from opscopilot_agent_runtime.llm.base import LlmNodeBase
from opscopilot_agent_runtime.state import AgentState


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


def _clarifier_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["proceed", "clarify"]},
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "tool_name": {"type": "string"},
                        "args": {"type": "object"},
                    },
                    "required": ["tool_name", "args"],
                },
            },
            "clarify_question": {"type": "string"},
            "missing_fields": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": ["action"],
    }


class LlmClarifier(LlmNodeBase):
    def __init__(
        self,
        provider: BedrockProvider,
        model_id: str,
        cost_table: dict,
        budget: BudgetEnforcer,
        ledger: CostLedger,
    ) -> None:
        super().__init__(provider, model_id, cost_table, budget, ledger)

    @staticmethod
    def from_env(provider: BedrockProvider) -> "LlmClarifier":
        model_id = _read_env("LLM_MODEL_ID")
        cost_table_path = _read_env("LLM_COST_TABLE_PATH")
        cost_table = load_cost_table(cost_table_path)
        budget = BudgetEnforcer(BudgetState(max_usd=_read_budget(), total_usd=0.0))
        ledger = CostLedger()
        return LlmClarifier(provider, model_id, cost_table, budget, ledger)

    def clarify(self, state: AgentState, tools: list[dict]) -> dict:
        if state.plan is None:
            raise RuntimeError("plan_missing")
        context = {
            "namespace": state.namespace,
            "label_selector": state.label_selector,
            "pod_name": state.pod_name,
            "container": state.container,
            "tail_lines": state.tail_lines,
        }
        context = {key: value for key, value in context.items() if value is not None}
        system_prompt = (
            "You normalize tool arguments to match the tool schemas exactly. "
            "Never return null for required arguments. "
            "If any required argument is missing or unknown, set action=clarify and include "
            "a clear clarify_question and a missing_fields list naming the required fields. "
            "Use any provided context fields as already-known values to fill required arguments. "
            "Only include arguments that exist in the tool's input_schema; do not invent keys. "
            "Do not guess missing values. "
            "Do not use any external knowledge or RAG context; only use the prompt and context fields."
        )
        request = LlmRequest(
            model_id=self._model_id,
            messages=[
                LlmMessage(role="system", content=system_prompt),
                LlmMessage(
                    role="user",
                    content=json.dumps(
                        {
                            "prompt": state.prompt,
                            "context": context,
                            "plan": {"steps": [step.__dict__ for step in state.plan.steps]},
                            "tools": tools,
                        }
                    ),
                ),
            ],
            response_format=LlmResponseFormat(type="json_schema", schema=_clarifier_schema()),
            temperature=0.0,
            max_tokens=256,
            idempotency_key=str(uuid.uuid4()),
            tags=LlmTags(session_id="clarifier", agent_run_id="clarifier", agent_node="clarifier"),
        )
        response = self._call(request=request, agent_node="clarifier", recorder=state.recorder)
        return response.output.json or {}
