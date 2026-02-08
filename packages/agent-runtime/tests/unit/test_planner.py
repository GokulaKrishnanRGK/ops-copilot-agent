from opscopilot_agent_runtime.mcp_client import MCPTool
from opscopilot_agent_runtime.planner import PlannerNode


class FakeMCPClient:
    def list_tools(self):
        return [MCPTool(name="k8s.list_pods", description="")]


def test_planner_uses_discovered_tools():
    planner = PlannerNode(client=FakeMCPClient())
    result = planner({})
    plan = result["plan"]
    assert plan.steps[0].tool_name == "k8s.list_pods"
