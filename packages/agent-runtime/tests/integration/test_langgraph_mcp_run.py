import os

import pytest

from opscopilot_agent_runtime.graph import AgentGraph
from opscopilot_agent_runtime.runtime import AgentRuntime, ExecutionLimits
from opscopilot_agent_runtime.mcp_client import MCPClient
from opscopilot_agent_runtime.nodes.planner_node import PlannerNode
from opscopilot_agent_runtime.nodes.planner_node import Plan, PlanStep
from opscopilot_agent_runtime.nodes.clarifier_node import ClarifierNode
from opscopilot_agent_runtime.nodes.tool_executor_node import ToolExecutorNode
from opscopilot_agent_runtime.state import AgentState
from opscopilot_agent_runtime.runtime.tool_registry import ToolRegistry


class _StaticClarifier:
    def __init__(self, namespace: str, label_selector: str) -> None:
        self._namespace = namespace
        self._label_selector = label_selector

    def clarify(self, state, tools, on_delta=None):  # noqa: ARG002
        return {
            "action": "proceed",
            "steps": [
                {
                    "tool_name": "k8s.list_pods",
                    "args": {
                        "namespace": self._namespace,
                        "label_selector": self._label_selector,
                    },
                }
            ],
        }

    def generate_clarify_question(  # noqa: ARG002
        self,
        prompt: str,
        missing_fields: list[str],
        recorder=None,
        on_delta=None,
    ) -> str:
        if missing_fields:
            return f"Please provide: {', '.join(missing_fields)}."
        return "Please provide additional details."


class _StaticPlanner:
    def plan(self, prompt, tool_names, recorder=None, on_delta=None):  # noqa: ARG002
        return Plan(
            steps=[
                PlanStep(
                    step_id="step-1",
                    tool_name="k8s.list_pods",
                    args={},
                )
            ]
        )


def test_langgraph_mcp_run_stream():
    if os.getenv("RUN_MCP_INTEGRATION") != "1":
        pytest.skip("RUN_MCP_INTEGRATION not enabled")
    if not os.getenv("MCP_BASE_URL"):
        pytest.skip("MCP_BASE_URL not set")
    namespace = os.getenv("MCP_NAMESPACE", "default")
    label_selector = os.getenv("MCP_LABEL_SELECTOR", "")
    client = MCPClient.from_env()
    graph = AgentGraph(
        tool_registry=ToolRegistry(client=client),
        planner=PlannerNode(llm_planner=_StaticPlanner()),
        clarifier=ClarifierNode(clarifier=_StaticClarifier(namespace, label_selector)),
        tool_executor=ToolExecutorNode(client=client),
        critic=None,
    )
    limits = ExecutionLimits(
        max_agent_steps=5,
        max_tool_calls=5,
        max_llm_calls=5,
        max_execution_time_ms=1000,
    )
    runtime = AgentRuntime(graph=graph, limits=limits)
    snapshots = list(
        runtime.run_stream(
            AgentState(
                prompt="list pods in default namespace",
                namespace=namespace,
                label_selector=label_selector,
            )
        )
    )
    assert snapshots
    assert snapshots[-1].tool_results is not None
    assert snapshots[-1].tool_results[0].tool_name == "k8s.list_pods"
