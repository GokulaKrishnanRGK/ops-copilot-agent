from dataclasses import dataclass

from .mcp_client import MCPClient
from .planner import Plan


@dataclass(frozen=True)
class ToolResult:
    step_id: str
    tool_name: str
    result: dict


def execute_plan(plan: Plan, client: MCPClient) -> dict:
    results: list[ToolResult] = []
    for step in plan.steps:
        response = client.call_tool(step.tool_name, step.args)
        results.append(
            ToolResult(step_id=step.step_id, tool_name=step.tool_name, result=response)
        )
    return {"tool_results": results}


class ToolExecutorNode:
    def __init__(self, client: MCPClient | None = None) -> None:
        self._client = client or MCPClient.from_env()

    def __call__(self, state: dict) -> dict:
        plan = state.get("plan")
        if plan is None:
            raise RuntimeError("plan_missing")
        return execute_plan(plan, self._client)
