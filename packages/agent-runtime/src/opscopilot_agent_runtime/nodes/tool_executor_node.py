from __future__ import annotations

import json
import os
from dataclasses import dataclass

from opscopilot_agent_runtime.mcp_client import MCPClient
from opscopilot_agent_runtime.persistence import AgentRunRecorder
from opscopilot_agent_runtime.runtime.logging import get_logger
from opscopilot_agent_runtime.state import AgentState
from opscopilot_agent_runtime.nodes.planner_node import Plan


@dataclass(frozen=True)
class ToolResult:
    step_id: str
    tool_name: str
    result: dict


def execute_plan(plan: Plan, client: MCPClient, recorder: AgentRunRecorder | None = None) -> list[ToolResult]:
    logger = get_logger(__name__)
    results: list[ToolResult] = []
    for step in plan.steps:
        if os.getenv("AGENT_DEBUG") == "1":
            logger.info(
                "tool_executor step=%s tool=%s args=%s",
                step.step_id,
                step.tool_name,
                json.dumps(step.args, default=str),
            )
        response = client.call_tool(step.tool_name, step.args)
        if os.getenv("AGENT_DEBUG") == "1":
            logger.info(
                "tool_executor result step=%s tool=%s response=%s",
                step.step_id,
                step.tool_name,
                json.dumps(response, default=str),
            )
        if recorder:
            recorder.record_tool_call(step.tool_name, step.args, response)
        results.append(
            ToolResult(step_id=step.step_id, tool_name=step.tool_name, result=response)
        )
    return results


class ToolExecutorNode:
    def __init__(self, client: MCPClient | None = None, recorder: AgentRunRecorder | None = None) -> None:
        self._client = client or MCPClient.from_env()
        self._recorder = recorder

    def __call__(self, state: AgentState) -> AgentState:
        if state.error:
            return state
        if state.plan is None:
            raise RuntimeError("plan_missing")
        recorder = self._recorder or state.recorder
        results = execute_plan(state.plan, self._client, recorder)
        return state.merge(tool_results=results)
