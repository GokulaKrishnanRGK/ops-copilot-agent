import os
import random
from collections.abc import Callable

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
    prompt_source_from_env,
)
from opscopilot_agent_runtime.persistence import AgentRunRecorder
from opscopilot_api.config_cache import RuntimeConfigData
from opscopilot_eval import LlmJudgeScorer, RagasScorer
from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer, BudgetState
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider
from opscopilot_observability import configure_langfuse


def _read_int(name: str, default_value: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default_value
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc


def _read_sample_rate() -> float:
    value = os.getenv("EVAL_SAMPLE_RATE", "0.1")
    try:
        sample_rate = float(value)
    except ValueError as exc:
        raise RuntimeError("EVAL_SAMPLE_RATE must be a number") from exc
    if sample_rate < 0 or sample_rate > 1:
        raise RuntimeError("EVAL_SAMPLE_RATE must be between 0 and 1")
    return sample_rate


class SampledAnswerScorer:
    def __init__(
        self,
        scorer: Callable,
        sample_rate: float,
        random_value: Callable[[], float] = random.random,
    ) -> None:
        self._scorer = scorer
        self._sample_rate = sample_rate
        self._random_value = random_value

    def __call__(self, state) -> None:
        if self._random_value() >= self._sample_rate:
            return
        self._scorer(state)


def _build_answer_scorer(provider: BedrockProvider, budget: BudgetEnforcer, ledger: CostLedger):
    sample_rate = _read_sample_rate()
    if sample_rate == 0:
        return None
    if not os.getenv("LANGFUSE_HOST"):
        return None
    langfuse = configure_langfuse()
    judge_scorer = None
    ragas_scorer = None
    if os.getenv("EVAL_LLM_JUDGE_ENABLED", "1") != "0":
        model_id = os.getenv("EVAL_JUDGE_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
        judge_scorer = LlmJudgeScorer(
            provider=provider,
            model_id=model_id,
            budget=budget,
            ledger=ledger,
            langfuse=langfuse,
        )
    if os.getenv("EVAL_RAGAS_ENABLED", "1") != "0":
        ragas_scorer = RagasScorer(langfuse=langfuse)
    if judge_scorer is None and ragas_scorer is None:
        return None

    def score_state(state):
        recorder = state.recorder
        session_id = recorder.session_id if recorder else "eval"
        run_id = recorder.run_id if recorder else "eval"
        langfuse.propagate_attributes(
            session_id=session_id,
            metadata={"agent_run_id": run_id},
            tags=["online_eval"],
        )
        if judge_scorer is not None:
            judge_scorer.score(
                prompt=state.prompt or "",
                answer=state.answer or "",
                tool_results=state.tool_results or [],
                rag_context=state.rag.text if state.rag else None,
                session_id=session_id,
                run_id=run_id,
                trace_id=state.langfuse_trace_id,
            )
        if ragas_scorer is not None and state.rag is not None:
            ragas_scorer.score(
                prompt=state.prompt or "",
                answer=state.answer or "",
                contexts=[result.text for result in state.rag.results],
                session_id=session_id,
                run_id=run_id,
                trace_id=state.langfuse_trace_id,
            )

    return SampledAnswerScorer(score_state, sample_rate)


class RuntimeFactory:
    def __init__(self, config: RuntimeConfigData) -> None:
        self._config = config

    def create(self, recorder: AgentRunRecorder) -> AgentRuntime:
        config = self._config
        provider = BedrockProvider()
        budget_max_usd = config.max_budget_usd
        max_usd = budget_max_usd if budget_max_usd is not None else float("inf")
        budget = BudgetEnforcer(BudgetState(max_usd=max_usd, total_usd=0.0))
        ledger = CostLedger()
        client = MCPClient.from_env()
        prompt_source = prompt_source_from_env()
        graph = AgentGraph(
            tool_registry=ToolRegistry(client=client),
            scope_check=ScopeCheckNode(
                classifier=ScopeClassifier(
                    provider=provider,
                    model_id=config.node("scope").model_id,
                    budget=budget,
                    ledger=ledger,
                    recorder=recorder,
                    prompt_source=prompt_source,
                    prompt_version=config.node("scope").prompt_version,
                )
            ),
            planner=PlannerNode(
                llm_planner=LlmPlanner(
                    provider=provider,
                    model_id=config.node("planner").model_id,
                    budget=budget,
                    ledger=ledger,
                    recorder=recorder,
                    prompt_source=prompt_source,
                    prompt_version=config.node("planner").prompt_version,
                )
            ),
            clarifier=ClarifierNode(
                clarifier=LlmClarifier(
                    provider=provider,
                    model_id=config.node("clarifier").model_id,
                    budget=budget,
                    ledger=ledger,
                    prompt_source=prompt_source,
                    prompt_version=config.node("clarifier").prompt_version,
                )
            ),
            tool_executor=ToolExecutorNode(client=client, recorder=recorder),
            answer=AnswerNode(
                synthesizer=AnswerSynthesizer(
                    provider=provider,
                    model_id=config.node("answer").model_id,
                    budget=budget,
                    ledger=ledger,
                    recorder=recorder,
                    prompt_source=prompt_source,
                    prompt_version=config.node("answer").prompt_version,
                )
            ),
            critic=None,
        )
        limits = ExecutionLimits(
            max_agent_steps=config.max_agent_steps,
            max_tool_calls=_read_int("AGENT_MAX_TOOL_CALLS", 10),
            max_llm_calls=_read_int("AGENT_MAX_LLM_CALLS", 10),
            max_execution_time_ms=_read_int("AGENT_MAX_EXECUTION_TIME_MS", 30_000),
        )
        return AgentRuntime(
            graph=graph,
            limits=limits,
            recorder=recorder,
            budget_max_usd=budget_max_usd,
            runtime_config_id=config.id,
            answer_scorer=_build_answer_scorer(provider, budget, ledger),
        )
