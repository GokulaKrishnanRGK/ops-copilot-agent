from opscopilot_agent_runtime.state import AgentState


class CriticNode:
    def __init__(self, enabled: bool = False):
        self.enabled = enabled

    def __call__(self, state: AgentState) -> AgentState:
        if not self.enabled:
            return state
        return state
