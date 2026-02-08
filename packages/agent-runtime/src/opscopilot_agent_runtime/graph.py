from dataclasses import dataclass
from typing import Callable

from langgraph.graph import END, StateGraph


PlannerFn = Callable[[dict], dict]
ToolExecutorFn = Callable[[dict], dict]
CriticFn = Callable[[dict], dict]


@dataclass(frozen=True)
class AgentGraph:
    planner: PlannerFn
    tool_executor: ToolExecutorFn
    critic: CriticFn | None = None

    def build(self):
        graph = StateGraph(dict)
        graph.add_node("planner", self.planner)
        graph.add_node("tool_executor", self.tool_executor)
        graph.set_entry_point("planner")
        graph.add_edge("planner", "tool_executor")
        if self.critic:
            graph.add_node("critic", self.critic)
            graph.add_edge("tool_executor", "critic")
            graph.add_edge("critic", END)
        else:
            graph.add_edge("tool_executor", END)
        return graph.compile()
