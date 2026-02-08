from .graph import AgentGraph
from .limits import ExecutionLimits, validate_limits


class AgentRuntime:
    def __init__(self, graph: AgentGraph, limits: ExecutionLimits):
        validate_limits(limits)
        self._graph = graph
        self._limits = limits

    def run(self, state: dict) -> dict:
        compiled = self._graph.build()
        result = compiled.invoke(state, config={"recursion_limit": self._limits.max_agent_steps})
        return result
