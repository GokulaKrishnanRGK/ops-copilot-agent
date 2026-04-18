from opscopilot_agent_runtime.graph import AgentGraph
from opscopilot_agent_runtime.mcp_client import MCPTool
from opscopilot_agent_runtime.nodes.answer_node import AnswerNode
from opscopilot_agent_runtime.nodes.clarifier_node import ClarifierNode
from opscopilot_agent_runtime.nodes.planner_node import Plan, PlannerNode, PlanStep
from opscopilot_agent_runtime.nodes.scope_check_node import ScopeCheckNode
from opscopilot_agent_runtime.nodes.tool_executor_node import ToolExecutorNode
from opscopilot_agent_runtime.runtime import AgentRuntime, ExecutionLimits
from opscopilot_agent_runtime.runtime.tool_registry import ToolRegistry
from opscopilot_agent_runtime.state import AgentState


class _FakeMCPClient:
    def list_tools(self):
        return [
            MCPTool(
                name="k8s.list_pods",
                description="List pods",
                input_schema={"properties": {"namespace": {"type": "string"}}, "required": []},
                output_schema=None,
            )
        ]

    def call_tool(self, _name: str, _args: dict) -> dict:
        return {
            "structured_content": {
                "status": "success",
                "result": {"items": [{"name": "hello-pod"}]},
            }
        }


class _StaticPlanner:
    def plan(self, prompt, tool_names, recorder=None, on_delta=None):  # noqa: ARG002
        return Plan(steps=[PlanStep(step_id="step-1", tool_name="k8s.list_pods", args={"namespace": "default"})])


class _TurnAwareClarifier:
    def __init__(self) -> None:
        self._call_count = 0

    def clarify(self, state, tools, on_delta=None):  # noqa: ARG002
        self._call_count += 1
        if self._call_count == 1:
            return {"action": "clarify", "clarify_question": "Which namespace and container?"}
        return {
            "action": "proceed",
            "steps": [{"tool_name": "k8s.list_pods", "args": {"namespace": "default"}}],
        }

    def generate_clarify_question(self, prompt, missing_fields, recorder=None, on_delta=None):  # noqa: ARG002
        return "Which namespace and container?"


class _StaticAnswerSynthesizer:
    def synthesize(self, prompt, tool_results, rag_context=None, recorder=None, on_delta=None):  # noqa: ARG002
        return "Pods retrieved successfully."


def _make_runtime(clarifier: _TurnAwareClarifier) -> AgentRuntime:
    client = _FakeMCPClient()
    graph = AgentGraph(
        tool_registry=ToolRegistry(client=client),
        scope_check=ScopeCheckNode(classifier=None),
        planner=PlannerNode(llm_planner=_StaticPlanner()),
        clarifier=ClarifierNode(clarifier=clarifier),
        tool_executor=ToolExecutorNode(client=client),
        answer=AnswerNode(synthesizer=_StaticAnswerSynthesizer()),
        critic=None,
    )
    return AgentRuntime(
        graph=graph,
        limits=ExecutionLimits(
            max_agent_steps=6,
            max_tool_calls=3,
            max_llm_calls=5,
            max_execution_time_ms=5000,
        ),
    )


def test_two_turn_clarification_flow():
    clarifier = _TurnAwareClarifier()
    runtime = _make_runtime(clarifier)

    first_snapshots = list(runtime.run_stream(AgentState(prompt="get pod logs")))
    assert first_snapshots
    first = first_snapshots[-1]
    assert first.error is not None
    assert first.error.get("type") == "clarification_required"

    second_snapshots = list(runtime.run_stream(first.merge(prompt="namespace=default container=hello")))
    assert second_snapshots
    second = second_snapshots[-1]
    assert second.error is None
    assert second.tool_results is not None
    assert second.tool_results[0].tool_name == "k8s.list_pods"
