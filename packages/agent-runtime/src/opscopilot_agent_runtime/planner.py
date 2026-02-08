from dataclasses import dataclass

from .events import AgentEvent, emit_event
from .mcp_client import MCPClient, MCPTool


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    tool_name: str
    args: dict


@dataclass(frozen=True)
class Plan:
    steps: list[PlanStep]


def plan(state: dict, tools: list[MCPTool] | None = None) -> dict:
    tool_name = tools[0].name if tools else "noop"
    plan_obj = Plan(steps=[PlanStep(step_id="step-1", tool_name=tool_name, args={})])
    event = AgentEvent(event_type="planner.completed", payload={"steps": len(plan_obj.steps)})
    return {"plan": plan_obj, **emit_event(event)}


class PlannerNode:
    def __init__(self, client: MCPClient | None = None) -> None:
        self._client = client

    def __call__(self, state: dict) -> dict:
        tools = self._client.list_tools() if self._client else None
        return plan(state, tools)
