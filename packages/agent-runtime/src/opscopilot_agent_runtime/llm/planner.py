from __future__ import annotations

import json
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

from typing import TYPE_CHECKING

from opscopilot_agent_runtime.persistence import AgentRunRecorder

from .base import LlmNodeBase

if TYPE_CHECKING:
    from opscopilot_agent_runtime.nodes.planner_node import Plan, PlanStep


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


def _plan_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "tool_name": {"type": "string"},
                    },
                    "required": ["tool_name"],
                },
            }
        },
        "required": ["steps"],
    }


class LlmPlanner(LlmNodeBase):
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
    ) -> "LlmPlanner":
        model_id = _read_env("LLM_MODEL_ID")
        cost_table_path = _read_env("LLM_COST_TABLE_PATH")
        cost_table = load_cost_table(cost_table_path)
        budget = BudgetEnforcer(BudgetState(max_usd=_read_budget(), total_usd=0.0))
        ledger = CostLedger()
        return LlmPlanner(provider, model_id, cost_table, budget, ledger, recorder=recorder)

    def plan(
        self,
        prompt: str,
        tool_names: list[str],
        recorder: AgentRunRecorder | None = None,
    ) -> Plan:
        system_prompt = (
            "You are a planning system that returns tool steps as JSON. "
            "Only use tool names from the provided list. "
            "If no tool is needed, return an empty steps array."
        )
        request = LlmRequest(
            model_id=self._model_id,
            messages=[
                LlmMessage(role="system", content=system_prompt),
                LlmMessage(
                    role="user",
                    content=json.dumps({"prompt": prompt, "tools": tool_names}),
                ),
            ],
            response_format=LlmResponseFormat(type="json_schema", schema=_plan_schema()),
            temperature=0.0,
            max_tokens=256,
            idempotency_key=str(uuid.uuid4()),
            tags=LlmTags(session_id="planner", agent_run_id="planner", agent_node="planner"),
        )
        response = self._call(
            request=request,
            agent_node="planner",
            recorder=recorder or self._recorder,
        )
        if response.error:
            raise RuntimeError(response.error.message)
        payload = response.output.json or {}
        from opscopilot_agent_runtime.nodes.planner_node import Plan, PlanStep

        steps = []
        for item in payload.get("steps", []):
            tool_name = item.get("tool_name")
            if not tool_name:
                continue
            steps.append(PlanStep(step_id=str(uuid.uuid4()), tool_name=tool_name, args={}))
        if not steps:
            return Plan(steps=[])
        return Plan(steps=steps)
