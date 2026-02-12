from langgraph.errors import GraphRecursionError

from opscopilot_agent_runtime.graph import AgentGraph
from opscopilot_agent_runtime.persistence import AgentRunRecorder
from opscopilot_agent_runtime.runtime.limits import ExecutionLimits, validate_limits
from opscopilot_agent_runtime.state import AgentState


class AgentRuntime:
    def __init__(
        self,
        graph: AgentGraph,
        limits: ExecutionLimits,
        recorder: AgentRunRecorder | None = None,
    ):
        validate_limits(limits)
        self._graph = graph
        self._limits = limits
        self._recorder = recorder

    def run(self, state: AgentState) -> AgentState:
        compiled = self._graph.build()
        recorder = self._recorder
        config_json = {"limits": {"max_agent_steps": self._limits.max_agent_steps}}
        if recorder:
            recorder.start(config_json)
        next_state = state
        if state.prompt:
            history = list(state.prompt_history or [])
            if not history or history[-1] != state.prompt:
                history.append(state.prompt)
            merged_prompt = "\n".join(history)
            next_state = next_state.merge(prompt=merged_prompt, prompt_history=history)
        if state.error and state.error.get("type") == "clarification_required" and state.prompt:
            next_state = next_state.merge(error=None)
        state_with_recorder = next_state.merge(recorder=recorder) if recorder else next_state
        try:
            result_dict = compiled.invoke(
                state_with_recorder.to_dict(),
                config={"recursion_limit": self._limits.max_agent_steps},
            )
            if recorder:
                recorder.finish("completed")
            return AgentState.from_dict(result_dict)
        except GraphRecursionError as exc:
            if recorder:
                recorder.finish("failed")
            return state_with_recorder.merge(
                error={
                    "type": "recursion_limit",
                    "message": str(exc),
                }
            )
        except Exception:
            if recorder:
                recorder.finish("failed")
            raise
