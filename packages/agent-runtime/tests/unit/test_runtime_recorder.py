from opscopilot_agent_runtime.graph import AgentGraph
from opscopilot_agent_runtime.runtime import AgentRuntime, ExecutionLimits
from opscopilot_agent_runtime.state import AgentState


class FakeRecorder:
    def __init__(self):
        self.started = False
        self.finished = None
        self.config = None

    def start(self, config_json):
        self.started = True
        self.config = config_json

    def finish(self, status):
        self.finished = status


def test_runtime_records_start_and_finish():
    def planner(state):
        return state.merge(plan="ok")

    def tool_executor(state):
        return state.merge(tool_results=[])

    graph = AgentGraph(planner=planner, tool_executor=tool_executor, clarifier=None)
    recorder = FakeRecorder()
    runtime = AgentRuntime(
        graph,
        ExecutionLimits(
            max_agent_steps=3,
            max_tool_calls=1,
            max_llm_calls=5,
            max_execution_time_ms=1000,
        ),
        recorder=recorder,
    )
    runtime.run(AgentState())
    assert recorder.started is True
    assert recorder.finished == "completed"
