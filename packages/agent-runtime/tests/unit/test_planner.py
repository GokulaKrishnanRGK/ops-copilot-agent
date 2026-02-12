from opscopilot_agent_runtime.mcp_client import MCPTool
from opscopilot_agent_runtime.nodes.planner_node import PlannerNode
from opscopilot_agent_runtime.state import AgentState


class FakeMCPClient:
    def list_tools(self):
        return [MCPTool(name="k8s.list_pods", description="", input_schema=None, output_schema=None)]


def test_planner_uses_discovered_tools():
    planner = PlannerNode()
    tools = FakeMCPClient().list_tools()
    result = planner(AgentState(tools=tools))
    plan = result.plan
    assert plan.steps[0].tool_name == "k8s.list_pods"
