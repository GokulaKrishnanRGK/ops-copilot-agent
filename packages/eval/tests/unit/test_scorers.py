from opscopilot_eval.scorers import (
    LlmJudgeScorer,
    RagasScorer,
    _build_ragas_embeddings,
    _build_ragas_llm,
    _litellm_model_name,
)
from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer, BudgetState
from opscopilot_llm_gateway.types import LlmOutput, LlmResponse


class FakeProvider:
    def __init__(self):
        self.requests = []

    def invoke(self, request):
        self.requests.append(request)
        return LlmResponse(
            output=LlmOutput(
                type="json",
                text=None,
                json={
                    "relevance": 4,
                    "groundedness": 5,
                    "comment": "Good answer.",
                },
            ),
            tokens_input=10,
            tokens_output=5,
            cost_usd=0.001,
            latency_ms=100,
            provider_metadata={"provider": "bedrock"},
            error=None,
        )


class FakeLangfuse:
    def __init__(self):
        self.scores = []

    def score_current_trace(self, **kwargs):
        self.scores.append(kwargs)

    def create_score(self, **kwargs):
        self.scores.append(kwargs)

    def propagate_attributes(self, **kwargs):
        return None

    def flush(self):
        return None


def test_llm_judge_scorer_scores_and_attaches_langfuse_scores():
    provider = FakeProvider()
    langfuse = FakeLangfuse()
    scorer = LlmJudgeScorer(
        provider=provider,
        model_id="anthropic.claude-3-haiku",
        budget=BudgetEnforcer(BudgetState(max_usd=1.0, total_usd=0.0)),
        ledger=CostLedger(),
        langfuse=langfuse,
    )

    result = scorer.score(
        prompt="list pods",
        answer="There is one pod.",
        tool_results=[{"tool_name": "k8s.list_pods", "result": {"pods": ["api"]}}],
        session_id="session-1",
        run_id="run-1",
        trace_id="trace-1",
    )

    assert result.relevance == 4
    assert result.groundedness == 5
    assert provider.requests[0].model_id == "anthropic.claude-3-haiku"
    assert provider.requests[0].tags.agent_node == "llm_judge"
    assert [score["name"] for score in langfuse.scores] == [
        "answer_relevance",
        "answer_groundedness",
    ]
    assert [score["value"] for score in langfuse.scores] == [4.0, 5.0]
    assert [score["trace_id"] for score in langfuse.scores] == ["trace-1", "trace-1"]
    assert [score["session_id"] for score in langfuse.scores] == ["session-1", "session-1"]


def test_llm_judge_scorer_rejects_invalid_scores():
    provider = FakeProvider()
    provider.invoke = lambda _request: LlmResponse(
        output=LlmOutput(type="json", text=None, json={"relevance": 6, "groundedness": 5}),
        tokens_input=1,
        tokens_output=1,
        cost_usd=0.0,
        latency_ms=1,
        provider_metadata={},
        error=None,
    )
    scorer = LlmJudgeScorer(
        provider=provider,
        model_id="anthropic.claude-3-haiku",
        budget=BudgetEnforcer(BudgetState(max_usd=1.0, total_usd=0.0)),
        ledger=CostLedger(),
        langfuse=FakeLangfuse(),
    )

    try:
        scorer.score(prompt="p", answer="a", tool_results=[])
    except ValueError as exc:
        assert "relevance" in str(exc)
    else:
        raise AssertionError("expected invalid relevance score to fail")


class FakeRagasMetric:
    def __init__(self, value):
        self.calls = []
        self._value = value

    async def ascore(self, **kwargs):
        self.calls.append(kwargs)
        return FakeRagasResult(self._value)


class FakeRagasResult:
    def __init__(self, value):
        self.value = value


def test_ragas_scorer_scores_and_attaches_langfuse_scores():
    faithfulness = FakeRagasMetric(0.8)
    answer_relevance = FakeRagasMetric(0.7)
    langfuse = FakeLangfuse()
    scorer = RagasScorer(
        faithfulness_metric=faithfulness,
        answer_relevance_metric=answer_relevance,
        langfuse=langfuse,
    )

    result = scorer.score(
        prompt="What is Ops Copilot?",
        answer="Ops Copilot diagnoses Kubernetes issues.",
        contexts=["Ops Copilot is a Kubernetes diagnostic assistant."],
        session_id="session-1",
        run_id="run-1",
        trace_id="trace-1",
    )

    assert result.faithfulness == 0.8
    assert result.answer_relevance == 0.7
    assert faithfulness.calls == [
        {
            "user_input": "What is Ops Copilot?",
            "response": "Ops Copilot diagnoses Kubernetes issues.",
            "retrieved_contexts": ["Ops Copilot is a Kubernetes diagnostic assistant."],
        }
    ]
    assert [score["name"] for score in langfuse.scores] == [
        "rag_faithfulness",
        "rag_answer_relevance",
    ]
    assert [score["value"] for score in langfuse.scores] == [0.8, 0.7]
    assert [score["trace_id"] for score in langfuse.scores] == ["trace-1", "trace-1"]


def test_ragas_scorer_skips_empty_contexts():
    scorer = RagasScorer(
        faithfulness_metric=FakeRagasMetric(0.8),
        answer_relevance_metric=FakeRagasMetric(0.7),
        langfuse=FakeLangfuse(),
    )

    result = scorer.score(prompt="p", answer="a", contexts=[])

    assert result is None


def test_ragas_factories_require_openai_key(monkeypatch):
    monkeypatch.setenv("RAGAS_LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("RAGAS_OPENAI_API_KEY", raising=False)

    try:
        _build_ragas_llm()
    except RuntimeError as exc:
        assert "RAGAS_OPENAI_API_KEY" in str(exc)
    else:
        raise AssertionError("expected missing RAGAS key to fail")


def test_ragas_factories_support_bedrock(monkeypatch):
    monkeypatch.setenv("RAGAS_LLM_PROVIDER", "bedrock")
    monkeypatch.setenv("RAGAS_LLM_MODEL", "global.amazon.nova-2-lite-v1:0")
    monkeypatch.setenv("RAGAS_EMBEDDING_PROVIDER", "bedrock")
    monkeypatch.setenv("RAGAS_EMBEDDING_MODEL", "amazon.titan-embed-text-v1")
    monkeypatch.setenv("RAGAS_BEDROCK_REGION", "us-east-1")

    llm = _build_ragas_llm()
    embeddings = _build_ragas_embeddings()

    assert llm.provider == "bedrock"
    assert llm.model == "bedrock/global.amazon.nova-2-lite-v1:0"
    assert embeddings.model == "bedrock/amazon.titan-embed-text-v1"


def test_litellm_model_name_preserves_existing_provider_prefix():
    assert _litellm_model_name("bedrock", "bedrock/amazon.titan-embed-text-v1") == (
        "bedrock/amazon.titan-embed-text-v1"
    )
