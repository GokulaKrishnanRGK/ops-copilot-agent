from opscopilot_agent_runtime.graph import AgentGraph
from opscopilot_agent_runtime.limits import ExecutionLimits
from opscopilot_agent_runtime.planner import PlannerNode
from opscopilot_agent_runtime.runtime import AgentRuntime
from opscopilot_agent_runtime.tool_executor import ToolExecutorNode


from opscopilot_agent_runtime.mcp_client import MCPTool


class FakeMCPClient:
    def list_tools(self):
        return [MCPTool(name="k8s.list_pods", description="")]

    def call_tool(self, _name: str, _arguments: dict) -> dict:
        return {"content": [{"type": "text", "text": "ok"}], "structured_content": {}}


def test_agent_runtime_runs_bounded_graph():
    graph = AgentGraph(
        planner=PlannerNode(client=FakeMCPClient()),
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
    result = runtime.run({})
    assert "tool_results" in result
    assert result["tool_results"][0].tool_name == "k8s.list_pods"
