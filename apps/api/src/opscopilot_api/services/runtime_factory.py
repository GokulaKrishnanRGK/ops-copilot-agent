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
    LlmInjectionClassifier,
    LlmPlanner,
    LlmTitleGenerator,
    MCPClient,
    NoOpTitleGenerator,
    PlannerNode,
    PromptInjectionGuard,
    ScopeCheckNode,
    ScopeClassifier,
    TitleGenerator,
    ToolExecutorNode,
    ToolRegistry,
    prompt_source_from_env,
)
from opscopilot_agent_runtime.runtime.rag import RagRetriever
from opscopilot_agent_runtime.history import PostgresSummaryStore
from opscopilot_agent_runtime.llm.summarizer import SummarizerLlmNode
from opscopilot_agent_runtime.persistence import AgentRunRecorder
from opscopilot_api.config_cache import RuntimeConfigData
from opscopilot_eval import LlmJudgeScorer, RagasScorer
from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer, BudgetState
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider
from opscopilot_observability import configure_langfuse


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


def _build_answer_scorer(config: RuntimeConfigData, provider: BedrockProvider, budget: BudgetEnforcer, ledger: CostLedger):
    if config.eval_sample_rate == 0:
        return None
    if not os.getenv("LANGFUSE_HOST"):
        return None
    langfuse = configure_langfuse()
    judge_scorer = None
    ragas_scorer = None
    if config.eval_llm_judge_enabled:
        judge_scorer = LlmJudgeScorer(
            provider=provider,
            model_id=config.eval_judge_model_id,
            budget=budget,
            ledger=ledger,
            langfuse=langfuse,
        )
    if config.eval_ragas_enabled:
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

    return SampledAnswerScorer(score_state, config.eval_sample_rate)


class RuntimeFactory:
    def __init__(self, config: RuntimeConfigData) -> None:
        self._config = config

    def build_title_generator(self) -> TitleGenerator:
        try:
            provider = BedrockProvider()
            budget = BudgetEnforcer(BudgetState(max_usd=0.01, total_usd=0.0))
            ledger = CostLedger()
            return LlmTitleGenerator(
                provider=provider,
                model_id=self._config.title_gen_model_id,
                budget=budget,
                ledger=ledger,
            )
        except Exception:
            return NoOpTitleGenerator()

    def create(self, recorder: AgentRunRecorder) -> AgentRuntime:
        config = self._config
        provider = BedrockProvider()
        budget_max_usd = config.max_budget_usd
        max_usd = budget_max_usd if budget_max_usd is not None else float("inf")
        budget = BudgetEnforcer(BudgetState(max_usd=max_usd, total_usd=0.0))
        ledger = CostLedger()
        client = MCPClient.from_env()
        prompt_source = prompt_source_from_env()
        rag_retriever: RagRetriever | None = None
        try:
            rag_retriever = RagRetriever.from_env(model_id=config.bedrock_embedding_model_id)
        except Exception:
            pass
        limits = ExecutionLimits(
            max_agent_steps=config.max_agent_steps,
            max_tool_calls=config.agent_max_tool_calls,
            max_llm_calls=config.agent_max_llm_calls,
            max_execution_time_ms=config.agent_max_execution_time_ms,
        )
        injection_classifier = None
        if config.prompt_injection_llm_check:
            injection_classifier = LlmInjectionClassifier(
                provider=provider,
                model_id=config.node("injection_classifier").model_id,
                budget=budget,
                ledger=ledger,
                recorder=recorder,
                prompt_source=prompt_source,
                prompt_version=config.node("injection_classifier").prompt_version,
            )
        graph = AgentGraph(
            tool_registry=ToolRegistry(client=client),
            injection_guard=PromptInjectionGuard(classifier=injection_classifier),
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
                ),
                rag_retriever=rag_retriever,
                max_steps=limits.max_agent_steps,
                max_llm_calls=limits.max_llm_calls,
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
        summarizer_node = SummarizerLlmNode(
            provider=provider,
            model_id=config.node("summarizer").model_id,
            budget=budget,
            ledger=ledger,
            prompt_source=prompt_source,
            prompt_version=config.summarizer_prompt_version,
        )
        from opscopilot_db.connection import get_sessionmaker
        summary_store = PostgresSummaryStore(get_sessionmaker())
        return AgentRuntime(
            graph=graph,
            limits=limits,
            recorder=recorder,
            budget_max_usd=budget_max_usd,
            runtime_config_id=config.id,
            answer_scorer=_build_answer_scorer(config, provider, budget, ledger),
            summarizer=summarizer_node,
            summary_store=summary_store,
            history_window_turns=config.history_window_turns,
        )
