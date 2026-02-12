from opscopilot_agent_runtime.llm.answer import AnswerSynthesizer
from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer, BudgetState
from opscopilot_llm_gateway.costs import CostEntry
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider, BedrockResult


class FakeRecorder:
    def __init__(self):
        self.llm_calls = 0
        self.budget_events = 0

    def record_llm_call(self, *args, **kwargs):
        self.llm_calls += 1

    def record_budget_event(self, *args, **kwargs):
        self.budget_events += 1


def _synthesizer(recorder=None):
    class FakeClient:
        def invoke(self, request):
            return BedrockResult(
                output_text=None,
                output_json={"answer": "ok"},
                tokens_input=1,
                tokens_output=1,
                cost_usd=0.0,
                latency_ms=1,
                provider_metadata={"model": request.model_id},
            )

    provider = BedrockProvider(FakeClient())
    return AnswerSynthesizer(
        provider=provider,
        model_id="model",
        cost_table={"model": CostEntry(model_id="model", input_per_1k=0.0, output_per_1k=0.0)},
        budget=BudgetEnforcer(BudgetState(max_usd=1.0, total_usd=0.0)),
        ledger=CostLedger(),
        recorder=recorder,
    )


def test_answer_synthesizer():
    synthesizer = _synthesizer()
    answer = synthesizer.synthesize("status", [])
    assert answer == "ok"


def test_answer_synthesizer_records_calls():
    recorder = FakeRecorder()
    synthesizer = _synthesizer(recorder=recorder)
    synthesizer.synthesize("status", [])
    assert recorder.llm_calls == 1
    assert recorder.budget_events == 1
