from opscopilot_agent_runtime.graph import AgentGraph
from opscopilot_agent_runtime.runtime import AgentRuntime, ExecutionLimits
from opscopilot_agent_runtime.runtime.events import AgentEvent
from opscopilot_agent_runtime.nodes.planner_node import PlannerNode
from opscopilot_agent_runtime.nodes.tool_executor_node import ToolExecutorNode
from opscopilot_agent_runtime.nodes.clarifier_node import ClarifierNode
from opscopilot_agent_runtime.state import AgentState
from opscopilot_agent_runtime.mcp_client import MCPTool
from opscopilot_agent_runtime.runtime.tool_registry import ToolRegistry


class FakeMCPClient:
    def list_tools(self):
        return [MCPTool(name="k8s.list_pods", description="", input_schema=None, output_schema=None)]

    def call_tool(self, _name: str, _arguments: dict) -> dict:
        return {"content": [{"type": "text", "text": "ok"}], "structured_content": {}}


def test_agent_runtime_runs_bounded_graph():
    registry = ToolRegistry(client=FakeMCPClient())
    graph = AgentGraph(
        tool_registry=registry,
        planner=PlannerNode(),
        clarifier=ClarifierNode(),
        tool_executor=ToolExecutorNode(client=FakeMCPClient()),
        critic=None,
    )
    limits = ExecutionLimits(
        max_agent_steps=5,
        max_tool_calls=5,
        max_llm_calls=5,
        max_execution_time_ms=1000,
    )
    runtime = AgentRuntime(graph=graph, limits=limits)
    snapshots = list(runtime.run_stream(AgentState()))
    assert snapshots
    result = snapshots[-1]
    assert result.tool_results is not None
    assert result.tool_results[0].tool_name == "k8s.list_pods"


def test_agent_runtime_run_stream_emits_progress_states():
    def planner(state):
        return state.merge(plan="ok", event=AgentEvent(event_type="planner.completed", payload={"steps": 1}))

    def tool_executor(state):
        return state.merge(
            tool_results=[{"tool_name": "k8s.list_pods"}],
            event=AgentEvent(event_type="tool_executor.completed", payload={"steps": 1}),
        )

    graph = AgentGraph(planner=planner, tool_executor=tool_executor, clarifier=None)
    runtime = AgentRuntime(
        graph=graph,
        limits=ExecutionLimits(
            max_agent_steps=5,
            max_tool_calls=5,
            max_llm_calls=5,
            max_execution_time_ms=1000,
        ),
    )

    snapshots = list(runtime.run_stream(AgentState()))
    assert len(snapshots) >= 2
    assert any(
        snapshot.event is not None and snapshot.event.event_type == "planner.completed"
        for snapshot in snapshots
    )
    assert snapshots[-1].tool_results is not None
