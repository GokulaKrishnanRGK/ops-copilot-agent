from dataclasses import dataclass
from typing import Callable

from langgraph.graph import END, StateGraph

from opscopilot_agent_runtime.state import AgentState
from opscopilot_agent_runtime.runtime.tool_registry import ToolRegistry


PlannerFn = Callable[[AgentState], AgentState]
ClarifierFn = Callable[[AgentState], AgentState]
ToolExecutorFn = Callable[[AgentState], AgentState]
CriticFn = Callable[[AgentState], AgentState]
AnswerFn = Callable[[AgentState], AgentState]
ScopeCheckFn = Callable[[AgentState], AgentState]


def _wrap(
    node: Callable[[AgentState], AgentState],
    tool_registry: ToolRegistry | None,
) -> Callable[[dict], dict]:
    def adapter(state_dict: dict) -> dict:
        state = AgentState.from_dict(state_dict)
        if tool_registry and state.tools is None:
            state = state.merge(tools=tool_registry.list_tools())
        updated = node(state)
        return updated.to_dict()

    return adapter


@dataclass(frozen=True)
class AgentGraph:
    planner: PlannerFn
    tool_executor: ToolExecutorFn
    scope_check: ScopeCheckFn | None = None
    clarifier: ClarifierFn | None = None
    answer: AnswerFn | None = None
    critic: CriticFn | None = None
    tool_registry: ToolRegistry | None = None

    def build(self):
        graph = StateGraph(dict)
        if self.scope_check:
            graph.add_node("scope_check", _wrap(self.scope_check, self.tool_registry))
        graph.add_node("planner", _wrap(self.planner, self.tool_registry))
        if self.clarifier:
            graph.add_node("clarifier", _wrap(self.clarifier, self.tool_registry))
        graph.add_node("tool_executor", _wrap(self.tool_executor, self.tool_registry))
        if self.answer:
            graph.add_node("answer", _wrap(self.answer, self.tool_registry))
        graph.set_entry_point("scope_check" if self.scope_check else "planner")
        if self.scope_check:
            graph.add_edge("scope_check", "planner")
        if self.clarifier:
            graph.add_edge("planner", "clarifier")
            graph.add_edge("clarifier", "tool_executor")
        else:
            graph.add_edge("planner", "tool_executor")
        if self.answer:
            graph.add_edge("tool_executor", "answer")
        if self.critic:
            graph.add_node("critic", _wrap(self.critic, self.tool_registry))
            if self.answer:
                graph.add_edge("answer", "critic")
            else:
                graph.add_edge("tool_executor", "critic")
            graph.add_edge("critic", END)
        else:
            if self.answer:
                graph.add_edge("answer", END)
            else:
                graph.add_edge("tool_executor", END)
        return graph.compile()
