from threading import Event

from opscopilot_agent_runtime.runtime import AgentRuntime, ExecutionLimits
from opscopilot_agent_runtime.state import AgentState


class FakeCompiledGraph:
    def stream(self, state, config, stream_mode):  # noqa: ARG002
        yield {**state, "answer": "final answer"}


class FakeGraph:
    def build(self):
        return FakeCompiledGraph()


def test_agent_runtime_invokes_answer_scorer_after_answer():
    called = Event()
    states = []

    def scorer(state):
        states.append(state)
        called.set()

    runtime = AgentRuntime(
        graph=FakeGraph(),
        limits=ExecutionLimits(
            max_agent_steps=5,
            max_tool_calls=5,
            max_llm_calls=5,
            max_execution_time_ms=1000,
        ),
        answer_scorer=scorer,
    )

    snapshots = list(runtime.run_stream(AgentState(prompt="status")))

    assert snapshots[-1].answer == "final answer"
    assert called.wait(1)
    assert states[0].answer == "final answer"
