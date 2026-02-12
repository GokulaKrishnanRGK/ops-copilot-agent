from __future__ import annotations

import uuid

from opscopilot_agent_runtime.llm.clarifier import LlmClarifier
from opscopilot_agent_runtime.nodes.planner_node import Plan, PlanStep
from opscopilot_agent_runtime.state import AgentState


class ClarifierNode:
    def __init__(self, clarifier: LlmClarifier | None = None) -> None:
        self._clarifier = clarifier

    def __call__(self, state: AgentState) -> AgentState:
        if state.error:
            return state
        if self._clarifier is None:
            return state
        if state.plan is None or not state.plan.steps:
            return state
        tools = state.tools or []
        planned_tools = {step.tool_name for step in state.plan.steps} if state.plan else set()
        if planned_tools:
            tools = [tool for tool in tools if tool.name in planned_tools]
        tool_payload = []
        for tool in tools:
            tool_payload.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.input_schema,
                    "output_schema": tool.output_schema,
                }
            )
        payload = self._clarifier.clarify(state, tool_payload)
        if payload.get("action") == "clarify":
            question = payload.get("clarify_question") or "clarification required"
            return state.merge(
                error={
                    "type": "clarification_required",
                    "message": question,
                }
            )
        missing_fields = payload.get("missing_fields")
        if isinstance(missing_fields, list) and missing_fields:
            question = payload.get("clarify_question")
            if not question:
                missing = ", ".join(str(field) for field in missing_fields)
                question = f"Please provide values for: {missing}."
            return state.merge(
                error={
                    "type": "clarification_required",
                    "message": question,
                }
            )
        steps = []
        for item in payload.get("steps", []):
            tool_name = item.get("tool_name")
            args = item.get("args")
            if not tool_name or not isinstance(args, dict):
                continue
            steps.append(PlanStep(step_id=str(uuid.uuid4()), tool_name=tool_name, args=args))
        if not steps:
            return state.merge(
                error={
                    "type": "clarification_required",
                    "message": "clarifier returned no steps",
                }
            )
        return state.merge(plan=Plan(steps=steps))
