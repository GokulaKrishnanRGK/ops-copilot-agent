from __future__ import annotations

import json
import uuid
from typing import Callable

from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider
from opscopilot_llm_gateway.types import (
    LlmMessage,
    LlmRequest,
    LlmResponseFormat,
    LlmTags,
)

from typing import TYPE_CHECKING

from opscopilot_agent_runtime.persistence import AgentRunRecorder
from opscopilot_agent_runtime.prompts import LocalYamlPromptSource, PromptSource, prompt_ref_for

from .base import LlmNodeBase
from .spotlight import wrap_user_input

if TYPE_CHECKING:
    from opscopilot_agent_runtime.nodes.planner_node import Plan, PlanStep


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
                    "additionalProperties": False,
                },
            }
        },
        "required": ["steps"],
        "additionalProperties": False,
    }


class LlmPlanner(LlmNodeBase):
    def __init__(
        self,
        provider: BedrockProvider,
        model_id: str,
        budget: BudgetEnforcer,
        ledger: CostLedger,
        recorder: AgentRunRecorder | None = None,
        prompt_source: PromptSource | None = None,
        prompt_version: str = "latest",
    ) -> None:
        super().__init__(provider, model_id, budget, ledger)
        self._recorder = recorder
        self._prompt_source = prompt_source or LocalYamlPromptSource()
        self._prompt_version = prompt_version

    def plan(
        self,
        prompt: str,
        tools: list[dict[str, str]],
        recorder: AgentRunRecorder | None = None,
        on_delta: Callable[[str], None] | None = None,
    ) -> Plan:
        system_prompt = self._prompt_source.get("planner", self._prompt_version)
        request = LlmRequest(
            model_id=self._model_id,
            messages=[
                LlmMessage(role="system", content=system_prompt, cache_control={"type": "ephemeral"}),
                LlmMessage(
                    role="user",
                    content=json.dumps({"prompt": wrap_user_input(prompt), "tools": tools}),
                ),
            ],
            response_format=LlmResponseFormat(type="json_schema", schema=_plan_schema()),
            temperature=0.0,
            max_tokens=256,
            idempotency_key=str(uuid.uuid4()),
            tags=LlmTags(session_id="planner", agent_run_id="planner", agent_node="planner"),
            prompt_ref=prompt_ref_for(self._prompt_source, "planner", self._prompt_version),
        )
        response = self._call(
            request=request,
            agent_node="planner",
            recorder=recorder or self._recorder,
            on_delta=on_delta,
        )
        if response.error:
            raise RuntimeError(response.error.message)
        payload = response.output.json or {}
        from opscopilot_agent_runtime.nodes.planner_node import Plan, PlanStep

        steps = []
        seen_tools: set[str] = set()
        for item in payload.get("steps", []):
            tool_name = item.get("tool_name")
            if not tool_name:
                continue
            if tool_name in seen_tools:
                continue
            seen_tools.add(tool_name)
            steps.append(PlanStep(step_id=str(uuid.uuid4()), tool_name=tool_name, args={}))
        if not steps:
            return Plan(steps=[])
        return Plan(steps=steps)
