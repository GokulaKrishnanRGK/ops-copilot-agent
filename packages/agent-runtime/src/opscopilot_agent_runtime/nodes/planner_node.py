from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from opscopilot_agent_runtime.runtime.events import AgentEvent
from opscopilot_agent_runtime.runtime.logging import get_logger
from opscopilot_agent_runtime.mcp_client import MCPTool
from opscopilot_agent_runtime.runtime.rag import RagRetriever
from opscopilot_agent_runtime.state import AgentState

if TYPE_CHECKING:
    from opscopilot_agent_runtime.llm.planner import LlmPlanner


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    tool_name: str
    args: dict


@dataclass(frozen=True)
class Plan:
    steps: list[PlanStep]


def _required_fields(schema: dict | None) -> list[str]:
    if not schema:
        return []
    required = schema.get("required")
    if isinstance(required, list):
        return [field for field in required if isinstance(field, str)]
    return []


def _build_args_from_state(state: AgentState, schema: dict | None) -> dict:
    if not schema:
        return {}
    props = schema.get("properties", {})
    args: dict[str, str] = {}
    if "namespace" in props and state.namespace is not None:
        args["namespace"] = state.namespace
    if "label_selector" in props and state.label_selector is not None:
        args["label_selector"] = state.label_selector
    return args


def plan(state: AgentState, tools: list[MCPTool] | None = None) -> AgentState:
    logger = get_logger(__name__)
    if not tools:
        return state.merge(
            error={"type": "planner_error", "message": "no tools available"},
        )
    best: tuple[MCPTool, dict, list[str]] | None = None
    for tool in tools:
        required = _required_fields(tool.input_schema)
        args = _build_args_from_state(state, tool.input_schema)
        if not set(required).issubset(args.keys()):
            continue
        if best is None or len(required) > len(best[2]):
            best = (tool, args, required)
    if best is None:
        return state.merge(
            error={"type": "planner_error", "message": "no compatible tool for state"},
        )
    tool, args, required = best
    if os.getenv("AGENT_DEBUG") == "1":
        logger.info(
            "planner fallback selected tool=%s required=%s args=%s",
            tool.name,
            required,
            json.dumps(args, default=str),
        )
    plan_obj = Plan(steps=[PlanStep(step_id="step-1", tool_name=tool.name, args=args)])
    event = AgentEvent(event_type="planner.completed", payload={"steps": len(plan_obj.steps)})
    return state.merge(plan=plan_obj, event=event)


class PlannerNode:
    def __init__(
        self,
        llm_planner: LlmPlanner | None = None,
        rag_retriever: RagRetriever | None = None,
    ) -> None:
        self._llm_planner = llm_planner
        if rag_retriever is None:
            try:
                rag_retriever = RagRetriever.from_env()
            except Exception as exc:
                logger = get_logger(__name__)
                logger.info("Exception creating Rag retriever: %s", exc)
                rag_retriever = None
        self._rag_retriever = rag_retriever

    def __call__(self, state: AgentState) -> AgentState:
        if state.error:
            return state
        tools = state.tools
        next_state = state
        if os.getenv("AGENT_DEBUG") == "1":
            logger = get_logger(__name__)
            logger.info(
                "planner: prompt_present=%s rag_retriever=%s rag_present=%s",
                bool(next_state.prompt),
                bool(self._rag_retriever),
                bool(next_state.rag),
            )
        if next_state.prompt and self._rag_retriever and next_state.rag is None:
            try:
                if os.getenv("AGENT_DEBUG") == "1":
                    logger = get_logger(__name__)
                    logger.info("planner: retrieving rag context")
                rag_context = self._rag_retriever.retrieve(next_state.prompt)
                next_state = next_state.merge(rag=rag_context)
            except Exception as exc:
                logger = get_logger(__name__)
                logger.info("rag retrieval skipped: %s", exc)
        if next_state.prompt and self._llm_planner:
            tool_names = [tool.name for tool in tools or []]
            plan_obj = self._llm_planner.plan(
                next_state.prompt,
                tool_names,
                recorder=next_state.recorder,
            )
            event = AgentEvent(event_type="planner.completed", payload={"steps": len(plan_obj.steps)})
            return next_state.merge(plan=plan_obj, event=event)
        return plan(next_state, tools)
