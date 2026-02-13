import os

import pytest

from opscopilot_agent_runtime.graph import AgentGraph
from opscopilot_agent_runtime.llm.answer import AnswerSynthesizer
from opscopilot_agent_runtime.llm.planner import LlmPlanner
from opscopilot_agent_runtime.llm.scope import ScopeClassifier
from opscopilot_agent_runtime.mcp_client import MCPClient
from opscopilot_agent_runtime.nodes.answer_node import AnswerNode
from opscopilot_agent_runtime.nodes.clarifier_node import ClarifierNode, \
  LlmClarifier
from opscopilot_agent_runtime.nodes.planner_node import PlannerNode
from opscopilot_agent_runtime.nodes.scope_check_node import ScopeCheckNode
from opscopilot_agent_runtime.nodes.tool_executor_node import ToolExecutorNode
from opscopilot_agent_runtime.runtime import AgentRuntime, ExecutionLimits
from opscopilot_agent_runtime.runtime.tool_registry import ToolRegistry
from opscopilot_agent_runtime.state import AgentState
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider, \
  build_bedrock_client


def test_clarifier_session_followup():
    if os.getenv("RUN_MCP_INTEGRATION") != "1":
        pytest.skip("RUN_MCP_INTEGRATION not enabled")
    if not os.getenv("MCP_BASE_URL"):
        pytest.skip("MCP_BASE_URL not set")
    if not os.getenv("LLM_MODEL_ID"):
        pytest.skip("LLM_MODEL_ID not set")
    if not os.getenv("LLM_COST_TABLE_PATH"):
        pytest.skip("LLM_COST_TABLE_PATH not set")
    if not os.getenv("AWS_REGION"):
        pytest.skip("AWS_REGION not set")

    client = MCPClient.from_env()
    registry = ToolRegistry(client=client)
    provider = BedrockProvider(build_bedrock_client())
    scope = ScopeClassifier.from_env(provider=provider)
    llm_planner = LlmPlanner.from_env(provider=provider)
    clarifier = LlmClarifier.from_env(provider=provider)
    answer = AnswerSynthesizer.from_env(provider=provider)

    graph = AgentGraph(
        tool_registry=registry,
        scope_check=ScopeCheckNode(classifier=scope),
        planner=PlannerNode(llm_planner=llm_planner),
        clarifier=ClarifierNode(clarifier=clarifier),
        tool_executor=ToolExecutorNode(client=client),
        answer=AnswerNode(synthesizer=answer),
        critic=None,
    )
    runtime = AgentRuntime(
        graph=graph,
        limits=ExecutionLimits(
            max_agent_steps=6,
            max_tool_calls=6,
            max_llm_calls=6,
            max_execution_time_ms=2000,
        ),
    )

    namespace = os.getenv("MCP_NAMESPACE", "default")
    state = AgentState(prompt="Whats the status of hello pod and get its logs from default namespace", namespace=namespace)
    first_snapshots = list(runtime.run_stream(state))
    assert first_snapshots
    first = first_snapshots[-1]
    assert first.error is not None
    assert first.error.get("type") == "clarification_required"

    followup_prompt = "Container is hello and get last 50 lines"
    second_snapshots = list(
        runtime.run_stream(
            first.merge(
                prompt=followup_prompt
            )
        )
    )
    assert second_snapshots
    second = second_snapshots[-1]
    # logger = get_logger(__name__)
    # logger.info("test_clarifier_session_followup state=%s", second)
    assert second.tool_results is not None
    result = second.tool_results[0].result.get("structured_content")
    assert result is not None
    assert result.get("status") == "success"
