import os

import pytest

from opscopilot_agent_runtime.graph import AgentGraph
from opscopilot_agent_runtime.llm.answer import AnswerSynthesizer
from opscopilot_agent_runtime.llm.planner import LlmPlanner
from opscopilot_agent_runtime.llm.scope import ScopeClassifier
from opscopilot_agent_runtime.mcp_client import MCPClient
from opscopilot_agent_runtime.nodes.answer_node import AnswerNode
from opscopilot_agent_runtime.nodes.clarifier_node import ClarifierNode, LlmClarifier
from opscopilot_agent_runtime.nodes.planner_node import PlannerNode
from opscopilot_agent_runtime.nodes.scope_check_node import ScopeCheckNode
from opscopilot_agent_runtime.nodes.tool_executor_node import ToolExecutorNode
from opscopilot_agent_runtime.runtime import AgentRuntime, ExecutionLimits
from opscopilot_agent_runtime.runtime.tool_registry import ToolRegistry
from opscopilot_agent_runtime.state import AgentState
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider, build_bedrock_client


def _embedding_provider() -> str:
    return os.getenv("LLM_EMBEDDING_PROVIDER", "openai").lower()


def _missing_env() -> list[str]:
    required = ["OPENSEARCH_URL", "OPENSEARCH_INDEX", "LLM_MODEL_ID", "LLM_COST_TABLE_PATH", "AWS_REGION"]
    provider = _embedding_provider()
    if provider == "openai":
        required += ["OPENAI_API_KEY", "OPENAI_EMBEDDING_MODEL"]
    if provider == "bedrock":
        required += ["BEDROCK_REGION", "BEDROCK_EMBEDDING_MODEL_ID"]
    return [name for name in required if not os.getenv(name)]


@pytest.mark.integration
def test_rag_retrieval_in_runtime(monkeypatch):
    missing = _missing_env()
    if missing:
        pytest.skip("missing env: " + ", ".join(missing))

    provider = BedrockProvider(build_bedrock_client())
    synthesizer = AnswerSynthesizer.from_env(provider=provider)
    llm_planner = LlmPlanner.from_env(provider=provider)
    clarifier = LlmClarifier.from_env(provider=provider)
    scope = ScopeClassifier.from_env(provider=provider)
    client = MCPClient.from_env()
    graph = AgentGraph(
        tool_registry=ToolRegistry(client=client),
        scope_check=ScopeCheckNode(classifier=scope),
        planner=PlannerNode(llm_planner=llm_planner),
        clarifier=ClarifierNode(clarifier=clarifier),
        tool_executor=ToolExecutorNode(client=client),
        answer=AnswerNode(synthesizer=synthesizer),
        critic=None,
    )
    runtime = AgentRuntime(
        graph=graph,
        limits=ExecutionLimits(
            max_agent_steps=6,
            max_tool_calls=3,
            max_llm_calls=5,
            max_execution_time_ms=2000,
        ),
    )
    snapshots = list(runtime.run_stream(AgentState(prompt="What is Ops Copilot?")))
    assert snapshots
    result = snapshots[-1]
    assert result.rag is not None
    assert result.answer
    assert result.citations
    assert any("ops-copilot-faq" in citation.source for citation in result.citations)
    assert any(citation.score > 0 for citation in result.citations)
    assert "ops" in result.answer.lower()
    assert "assistant" in result.answer.lower()
