from opscopilot_eval.scorers import LlmJudgeScorer
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
