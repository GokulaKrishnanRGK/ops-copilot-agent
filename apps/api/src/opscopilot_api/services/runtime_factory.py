import os

from opscopilot_agent_runtime import (
    AgentGraph,
    AgentRuntime,
    AnswerNode,
    AnswerSynthesizer,
    ClarifierNode,
    ExecutionLimits,
    LlmClarifier,
    LlmPlanner,
    MCPClient,
    PlannerNode,
    ScopeCheckNode,
    ScopeClassifier,
    ToolExecutorNode,
    ToolRegistry,
)
from opscopilot_agent_runtime.persistence import AgentRunRecorder
from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer, BudgetState
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider


def _read_int(name: str, default_value: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default_value
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc


def _read_budget() -> float:
    value = os.getenv("LLM_MAX_BUDGET_USD", "1.0")
    try:
        return float(value)
    except ValueError as exc:
        raise RuntimeError("LLM_MAX_BUDGET_USD must be a number") from exc


class RuntimeFactory:
    def create(self, recorder: AgentRunRecorder) -> AgentRuntime:
        provider = BedrockProvider()
        budget_max_usd = _read_budget()
        budget = BudgetEnforcer(BudgetState(max_usd=budget_max_usd, total_usd=0.0))
        ledger = CostLedger()
        client = MCPClient.from_env()
        graph = AgentGraph(
            tool_registry=ToolRegistry(client=client),
            scope_check=ScopeCheckNode(classifier=ScopeClassifier.from_env(provider=provider, budget=budget, ledger=ledger, recorder=recorder)),
            planner=PlannerNode(llm_planner=LlmPlanner.from_env(provider=provider, budget=budget, ledger=ledger, recorder=recorder)),
            clarifier=ClarifierNode(clarifier=LlmClarifier.from_env(provider=provider, budget=budget, ledger=ledger)),
            tool_executor=ToolExecutorNode(client=client, recorder=recorder),
            answer=AnswerNode(synthesizer=AnswerSynthesizer.from_env(provider=provider, budget=budget, ledger=ledger, recorder=recorder)),
            critic=None,
        )
        limits = ExecutionLimits(
            max_agent_steps=_read_int("AGENT_MAX_STEPS", 10),
            max_tool_calls=_read_int("AGENT_MAX_TOOL_CALLS", 10),
            max_llm_calls=_read_int("AGENT_MAX_LLM_CALLS", 10),
            max_execution_time_ms=_read_int("AGENT_MAX_EXECUTION_TIME_MS", 30_000),
        )
        return AgentRuntime(graph=graph, limits=limits, recorder=recorder, budget_max_usd=budget_max_usd)
