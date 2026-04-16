import json
from unittest.mock import MagicMock, patch

from opscopilot_agent_runtime.llm.answer import AnswerSynthesizer
from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer, BudgetState
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider


class FakeRecorder:
    def __init__(self):
        self.session_id = "test-session"
        self.run_id = "test-run"
        self.llm_calls = 0
        self.budget_events = 0

    def record_llm_call(self, *args, **kwargs):
        self.llm_calls += 1

    def record_budget_event(self, *args, **kwargs):
        self.budget_events += 1


def _mock_litellm_response(content: str):
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = content
    resp.usage = MagicMock()
    resp.usage.prompt_tokens = 10
    resp.usage.completion_tokens = 5
    resp._hidden_params = {"response_cost": 0.001}
    resp.model = "model"
    return resp


def _synthesizer(recorder=None):
    provider = BedrockProvider()
    budget = BudgetEnforcer(BudgetState(max_usd=1.0, total_usd=0.0))
    ledger = CostLedger()
    return AnswerSynthesizer(
        provider=provider,
        model_id="anthropic.claude-3-sonnet",
        budget=budget,
        ledger=ledger,
        recorder=recorder,
    )


def test_answer_synthesizer():
    with patch("litellm.completion", return_value=_mock_litellm_response(json.dumps({"answer": "ok"}))):
        synthesizer = _synthesizer()
        answer = synthesizer.synthesize("status", [])

    assert answer == "ok"


def test_answer_synthesizer_records_calls():
    recorder = FakeRecorder()
    with patch("litellm.completion", return_value=_mock_litellm_response(json.dumps({"answer": "ok"}))):
        synthesizer = _synthesizer(recorder=recorder)
        synthesizer.synthesize("status", [])

    assert recorder.llm_calls == 1
    assert recorder.budget_events == 1
