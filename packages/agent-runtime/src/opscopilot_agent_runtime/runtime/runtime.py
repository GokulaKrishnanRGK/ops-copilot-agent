from langgraph.errors import GraphRecursionError

from opscopilot_agent_runtime.graph import AgentGraph
from opscopilot_agent_runtime.persistence import AgentRunRecorder
from opscopilot_agent_runtime.runtime.limits import ExecutionLimits, validate_limits
from opscopilot_agent_runtime.runtime.logging import clear_log_context, set_log_context
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

    def _prepare_state(self, state: AgentState) -> tuple[AgentState, AgentRunRecorder | None]:
        recorder = self._recorder
        config_json = {"limits": {"max_agent_steps": self._limits.max_agent_steps}}
        if recorder:
            recorder.start(config_json)
            set_log_context(recorder.session_id, recorder.run_id)
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
        return state_with_recorder, recorder

    def run(self, state: AgentState) -> AgentState:
        last_state = state
        for snapshot in self.run_stream(state):
            last_state = snapshot
        return last_state

    def run_stream(self, state: AgentState):
        compiled = self._graph.build()
        state_with_recorder, recorder = self._prepare_state(state)
        try:
            final_state: AgentState | None = None
            for result_dict in compiled.stream(
                state_with_recorder.to_dict(),
                config={"recursion_limit": self._limits.max_agent_steps},
                stream_mode="values",
            ):
                final_state = AgentState.from_dict(result_dict)
                yield final_state
            if recorder:
                recorder.finish("completed")
            if final_state is None:
                yield state_with_recorder
        except GraphRecursionError as exc:
            if recorder:
                recorder.finish("failed")
            yield state_with_recorder.merge(
                error={
                    "type": "recursion_limit",
                    "message": str(exc),
                }
            )
        except Exception:
            if recorder:
                recorder.finish("failed")
            raise
        finally:
            clear_log_context()
