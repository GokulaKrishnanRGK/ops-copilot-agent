from opscopilot_agent_runtime.llm.planner import LlmPlanner
from opscopilot_agent_runtime.persistence import AgentRunRecorder
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


def _planner(recorder: AgentRunRecorder | None = None):
    class FakeClient:
        def invoke(self, request):
            return BedrockResult(
                output_text=None,
                output_json={
                    "steps": [
                        {"tool_name": "k8s.list_pods", "args": {"namespace": "default", "label_selector": ""}}
                    ]
                },
                tokens_input=1,
                tokens_output=1,
                cost_usd=0.0,
                latency_ms=1,
                provider_metadata={"model": request.model_id},
            )

    provider = BedrockProvider(FakeClient())
    return LlmPlanner(
        provider=provider,
        model_id="model",
        cost_table={"model": CostEntry(model_id="model", input_per_1k=0.0, output_per_1k=0.0)},
        budget=BudgetEnforcer(BudgetState(max_usd=1.0, total_usd=0.0)),
        ledger=CostLedger(),
        recorder=recorder,
    )


def test_llm_planner_builds_plan():
    planner = _planner()
    plan = planner.plan("check pods", ["k8s.list_pods"])
    assert plan.steps[0].tool_name == "k8s.list_pods"
    assert plan.steps[0].args["namespace"] == "default"


def test_llm_planner_records_calls():
    recorder = FakeRecorder()
    planner = _planner(recorder=recorder)
    planner.plan("check pods", ["k8s.list_pods"])
    assert recorder.llm_calls == 1
    assert recorder.budget_events == 1
