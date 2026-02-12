from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opscopilot_agent_runtime.runtime.events import AgentEvent
    from opscopilot_agent_runtime.persistence import AgentRunRecorder
    from opscopilot_agent_runtime.nodes.tool_executor_node import ToolResult
    from opscopilot_agent_runtime.nodes.planner_node import Plan
    from opscopilot_agent_runtime.mcp_client import MCPTool
    from opscopilot_agent_runtime.runtime.rag import RagContext
    from opscopilot_rag.types import Citation


@dataclass(frozen=True)
class AgentState:
    prompt: str | None = None
    prompt_history: list[str] | None = None
    plan: Plan | None = None
    tool_results: list[ToolResult] | None = None
    answer: str | None = None
    rag: RagContext | None = None
    citations: list[Citation] | None = None
    namespace: str | None = None
    label_selector: str | None = None
    pod_name: str | None = None
    container: str | None = None
    tail_lines: int | None = None
    tools: list[MCPTool] | None = None
    recorder: AgentRunRecorder | None = None
    event: AgentEvent | None = None
    error: dict | None = None

    def merge(self, **kwargs) -> "AgentState":
        return replace(self, **kwargs)

    def to_dict(self) -> dict:
        return {
            "prompt": self.prompt,
            "prompt_history": self.prompt_history,
            "plan": self.plan,
            "tool_results": self.tool_results,
            "answer": self.answer,
            "rag": self.rag,
            "citations": self.citations,
            "namespace": self.namespace,
            "label_selector": self.label_selector,
            "pod_name": self.pod_name,
            "container": self.container,
            "tail_lines": self.tail_lines,
            "tools": self.tools,
            "recorder": self.recorder,
            "event": self.event,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "AgentState":
        return cls(
            prompt=payload.get("prompt"),
            prompt_history=payload.get("prompt_history"),
            plan=payload.get("plan"),
            tool_results=payload.get("tool_results"),
            answer=payload.get("answer"),
            rag=payload.get("rag"),
            citations=payload.get("citations"),
            namespace=payload.get("namespace"),
            label_selector=payload.get("label_selector"),
            pod_name=payload.get("pod_name"),
            container=payload.get("container"),
            tail_lines=payload.get("tail_lines"),
            tools=payload.get("tools"),
            recorder=payload.get("recorder"),
            event=payload.get("event"),
            error=payload.get("error"),
        )
