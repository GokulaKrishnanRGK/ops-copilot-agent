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

    def clarify(
        self,
        state: AgentState,
        tools: list[dict],
        on_delta: Callable[[str], None] | None = None,
    ) -> dict:
        if state.plan is None:
            raise RuntimeError("plan_missing")
        known_args = {
            "namespace": state.namespace,
            "label_selector": state.label_selector,
            "pod_name": state.pod_name,
            "container": state.container,
            "tail_lines": state.tail_lines,
        }
        known_args = {key: value for key, value in known_args.items() if value is not None}
        system_prompt = (
            "You normalize tool arguments to match the tool schemas exactly. "
            "Read the user prompt first and extract argument values directly from that prompt. "
            "Use known_args only as fallback when prompt does not provide a value. "
            "Never use FAQ/docs/RAG/tool descriptions as source values for arguments. "
            "Never return null for required arguments. "
            "If any required argument is missing or unknown, set action=clarify and include "
            "a missing_fields list naming the missing required fields. "
            "Only include arguments that exist in the tool's input_schema; do not invent keys. "
            "Do not guess missing values. "
            "If prompt text contains namespace (example: 'in default namespace'), do not ask for namespace. "
            "Clarify only when required fields are missing in both prompt and known_args. "
            "Do NOT mention internal tool names (such as k8s.*), schema field names "
            "(such as namespace, pod_name, label_selector, tail_lines, deployment_name), "
            "or implementation details."
        )
        planned_steps = [{"tool_name": step.tool_name} for step in state.plan.steps]
        request = LlmRequest(
            model_id=self._model_id,
            messages=[
                LlmMessage(role="system", content=system_prompt),
                LlmMessage(
                    role="user",
                    content=json.dumps(
                        {
                            "prompt": state.prompt,
                            "known_args": known_args,
                            "plan": {"steps": planned_steps},
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
        response = self._call(
            request=request,
            agent_node="clarifier",
            recorder=state.recorder,
        )
        payload = response.output.json or {}
        action = payload.get("action")
        if action == "clarify":
            payload["clarify_question"] = self.generate_clarify_question(
                prompt=state.prompt or "",
                missing_fields=payload.get("missing_fields") if isinstance(payload.get("missing_fields"), list) else [],
                recorder=state.recorder,
                on_delta=on_delta,
            )
        return payload

    def generate_clarify_question(
        self,
        prompt: str,
        missing_fields: list[str],
        recorder: AgentRunRecorder | None = None,
        on_delta: Callable[[str], None] | None = None,
    ) -> str:
        request = LlmRequest(
            model_id=self._model_id,
            messages=[
                LlmMessage(
                    role="system",
                    content=(
                        "Write one concise clarification question for the user in natural English. "
                        "Ask specifically for what is missing so execution can continue. "
                        "Do not mention internal tool names, schema names, or implementation details."
                    ),
                ),
                LlmMessage(
                    role="user",
                    content=json.dumps(
                        {
                            "prompt": prompt,
                            "missing_fields": missing_fields,
                        }
                    ),
                ),
            ],
            response_format=LlmResponseFormat(type="text", schema=None),
            temperature=0.0,
            max_tokens=128,
            idempotency_key=str(uuid.uuid4()),
            tags=LlmTags(session_id="clarifier", agent_run_id="clarifier", agent_node="clarifier_question"),
        )
        response = self._call(
            request=request,
            agent_node="clarifier_question",
            recorder=recorder,
            on_delta=on_delta,
        )
        question = (response.output.text or "").strip()
        if question:
            return question
        raise RuntimeError("clarify question missing")
