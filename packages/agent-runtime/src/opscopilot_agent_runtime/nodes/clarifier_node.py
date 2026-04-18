from __future__ import annotations

import uuid

from opscopilot_agent_runtime.llm.clarifier import LlmClarifier
from opscopilot_agent_runtime.nodes.planner_node import Plan, PlanStep
from opscopilot_agent_runtime.runtime.events import AgentEvent
from opscopilot_agent_runtime.runtime.logging import get_logger
from opscopilot_agent_runtime.state import AgentState

_logger = get_logger(__name__)


def _required_fields(schema: dict | None) -> set[str]:
    if not schema:
        return set()
    required = schema.get("required")
    if not isinstance(required, list):
        return set()
    return {field for field in required if isinstance(field, str)}


def _allowed_fields(schema: dict | None) -> set[str]:
    if not schema:
        return set()
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return set()
    return {field for field in properties.keys() if isinstance(field, str)}


class ClarifierNode:
    def __init__(self, clarifier: LlmClarifier | None = None) -> None:
        self._clarifier = clarifier

    def __call__(self, state: AgentState) -> AgentState:
        if state.error:
            _logger.debug("clarifier: skipped existing_error=%s", state.error.get("type"))
            return state
        if self._clarifier is None:
            _logger.debug("clarifier: skipped no_clarifier")
            return state
        if state.plan is None or not state.plan.steps:
            _logger.debug("clarifier: skipped no_plan")
            return state
        _logger.debug("clarifier: enter plan_steps=%d prompt_len=%d", len(state.plan.steps), len(state.prompt or ""))
        tools = state.tools or []
        planned_tools = {step.tool_name for step in state.plan.steps} if state.plan else set()
        if planned_tools:
            tools = [tool for tool in tools if tool.name in planned_tools]
        tool_payload = []
        for tool in tools:
            input_schema = tool.input_schema or {}
            required = input_schema.get("required")
            properties = input_schema.get("properties")
            tool_payload.append(
                {
                    "name": tool.name,
                    "input_schema": {
                        "required": required if isinstance(required, list) else [],
                        "properties": properties if isinstance(properties, dict) else {},
                    },
                }
            )
        _logger.debug(
            "clarifier: schema_built tool_count=%d tools=%s",
            len(tool_payload),
            [{t["name"]: t["input_schema"]["required"]} for t in tool_payload],
        )
        on_delta = None
        if state.llm_stream_callback is not None:
            on_delta = lambda text: state.llm_stream_callback("clarifier_question", text)
        payload = self._clarifier.clarify(state, tool_payload, on_delta=on_delta)
        _logger.debug(
            "clarifier: llm_response action=%s missing_fields=%s steps=%d",
            payload.get("action"),
            payload.get("missing_fields"),
            len(payload.get("steps") or []),
        )
        if payload.get("action") == "clarify":
            question = payload.get("clarify_question")
            if not isinstance(question, str) or not question.strip():
                raise RuntimeError("clarifier question missing")
            return state.merge(
                event=AgentEvent(
                    event_type="clarifier.clarification_required",
                    payload={"question": question},
                ),
                error={
                    "type": "clarification_required",
                    "message": question,
                }
            )
        missing_fields = payload.get("missing_fields")
        if isinstance(missing_fields, list) and missing_fields:
            question = payload.get("clarify_question")
            if not isinstance(question, str) or not question.strip():
                question = self._clarifier.generate_clarify_question(
                    prompt=state.prompt or "",
                    missing_fields=missing_fields,
                    recorder=state.recorder,
                    on_delta=on_delta,
                )
            return state.merge(
                event=AgentEvent(
                    event_type="clarifier.clarification_required",
                    payload={"question": question},
                ),
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
            question = self._clarifier.generate_clarify_question(
                prompt=state.prompt or "",
                missing_fields=missing_fields if isinstance(missing_fields, list) else [],
                recorder=state.recorder,
                on_delta=on_delta,
            )
            return state.merge(
                event=AgentEvent(
                    event_type="clarifier.clarification_required",
                    payload={"question": question},
                ),
                error={
                    "type": "clarification_required",
                    "message": question,
                },
            )
        tool_map = {tool.name: tool for tool in tools}
        for step in steps:
            _logger.debug(
                "clarifier: validate_step tool=%s args=%s",
                step.tool_name,
                list(step.args.keys()),
            )
            tool = tool_map.get(step.tool_name)
            if tool is None:
                _logger.debug("clarifier: tool_not_found tool=%s", step.tool_name)
                question = self._clarifier.generate_clarify_question(
                    prompt=state.prompt or "",
                    missing_fields=[],
                    recorder=state.recorder,
                    on_delta=on_delta,
                )
                return state.merge(
                    event=AgentEvent(
                        event_type="clarifier.clarification_required",
                        payload={"question": question},
                    ),
                    error={
                        "type": "clarification_required",
                        "message": question,
                    }
                )
            required = _required_fields(tool.input_schema)
            allowed = _allowed_fields(tool.input_schema)
            missing = sorted(field for field in required if field not in step.args)
            extra = sorted(field for field in step.args.keys() if field not in allowed)
            _logger.debug(
                "clarifier: field_check tool=%s required=%s provided=%s missing=%s extra=%s",
                step.tool_name,
                sorted(required),
                sorted(step.args.keys()),
                missing,
                extra,
            )
            if missing:
                question = self._clarifier.generate_clarify_question(
                    prompt=state.prompt or "",
                    missing_fields=missing,
                    recorder=state.recorder,
                    on_delta=on_delta,
                )
                return state.merge(
                    event=AgentEvent(
                        event_type="clarifier.clarification_required",
                        payload={"question": question},
                    ),
                    error={
                        "type": "clarification_required",
                        "message": question,
                    }
                )
            if extra:
                question = self._clarifier.generate_clarify_question(
                    prompt=state.prompt or "",
                    missing_fields=extra,
                    recorder=state.recorder,
                    on_delta=on_delta,
                )
                return state.merge(
                    event=AgentEvent(
                        event_type="clarifier.clarification_required",
                        payload={"question": question},
                    ),
                    error={
                        "type": "clarification_required",
                        "message": question,
                    }
                )
        _logger.debug("clarifier: completed steps=%d", len(steps))
        return state.merge(
            plan=Plan(steps=steps),
            event=AgentEvent(event_type="clarifier.completed", payload={"steps": len(steps)}),
        )
