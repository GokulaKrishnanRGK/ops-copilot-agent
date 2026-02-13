import logging
import os
import uuid

import pytest

from opscopilot_agent_runtime.nodes.answer_node import AnswerNode
from opscopilot_agent_runtime.llm.answer import AnswerSynthesizer
from opscopilot_agent_runtime.graph import AgentGraph
from opscopilot_agent_runtime.runtime import ExecutionLimits
from opscopilot_agent_runtime.llm.planner import LlmPlanner
from opscopilot_agent_runtime.llm.scope import ScopeClassifier
from opscopilot_agent_runtime.mcp_client import MCPClient
from opscopilot_agent_runtime.persistence import AgentRunRecorder
from opscopilot_agent_runtime.nodes.planner_node import PlannerNode
from opscopilot_agent_runtime.nodes.clarifier_node import ClarifierNode, LlmClarifier
from opscopilot_agent_runtime.nodes.scope_check_node import ScopeCheckNode
from opscopilot_agent_runtime.runtime import AgentRuntime
from opscopilot_agent_runtime.nodes.tool_executor_node import ToolExecutorNode
from opscopilot_agent_runtime.runtime.tool_registry import ToolRegistry
from opscopilot_agent_runtime.state import AgentState
from opscopilot_db import models
from opscopilot_db.base import Base
from opscopilot_db.connection import get_engine, get_sessionmaker
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider, build_bedrock_client


def _ensure_schema():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def _count(db, model, run_id: str) -> int:
    return db.query(model).filter(model.agent_run_id == run_id).count()


def test_prompt_run_persists_steps():
    if os.getenv("RUN_MCP_INTEGRATION") != "1":
        pytest.skip("RUN_MCP_INTEGRATION not enabled")
    if not os.getenv("MCP_BASE_URL"):
        pytest.skip("MCP_BASE_URL not set")
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    if not os.getenv("LLM_MODEL_ID"):
        pytest.skip("LLM_MODEL_ID not set")
    if not os.getenv("LLM_COST_TABLE_PATH"):
        pytest.skip("LLM_COST_TABLE_PATH not set")
    if not os.getenv("AWS_REGION"):
        pytest.skip("AWS_REGION not set")
    if os.getenv("LLM_DEBUG") == "1":
        logging.basicConfig(level=logging.INFO)

    _ensure_schema()
    run_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    recorder = AgentRunRecorder(session_id=session_id, run_id=run_id)

    provider = BedrockProvider(build_bedrock_client())
    llm_planner = LlmPlanner.from_env(provider=provider, recorder=recorder)
    answer_synthesizer = AnswerSynthesizer.from_env(provider=provider, recorder=recorder)
    clarifier = LlmClarifier.from_env(provider=provider)
    scope_classifier = ScopeClassifier.from_env(provider=provider, recorder=recorder)

    client = MCPClient.from_env()
    graph = AgentGraph(
        tool_registry=ToolRegistry(client=client),
        scope_check=ScopeCheckNode(classifier=scope_classifier),
        planner=PlannerNode(llm_planner=llm_planner),
        clarifier=ClarifierNode(clarifier=clarifier),
        tool_executor=ToolExecutorNode(client=client, recorder=recorder),
        answer=AnswerNode(synthesizer=answer_synthesizer),
        critic=None,
    )
    runtime = AgentRuntime(
        graph=graph,
        limits=ExecutionLimits(
            max_agent_steps=10,
            max_tool_calls=5,
            max_llm_calls=5,
            max_execution_time_ms=2000,
        ),
        recorder=recorder,
    )

    namespace = os.getenv("MCP_NAMESPACE", "default")
    label_selector = os.getenv("MCP_LABEL_SELECTOR", "")
    result = runtime.run(
        AgentState(
            prompt="List pods in default namespace with label selector app=hello",
            namespace=namespace,
            label_selector=label_selector,
        )
    )
    print(result)
    assert result.answer is not None

    sessionmaker = get_sessionmaker()
    with sessionmaker() as db:
        run = db.get(models.AgentRun, run_id)
        assert run is not None
        assert run.status == "completed"
        assert _count(db, models.ToolCall, run_id) >= 0
        assert _count(db, models.LlmCall, run_id) >= 1
        assert _count(db, models.BudgetEvent, run_id) >= 1
