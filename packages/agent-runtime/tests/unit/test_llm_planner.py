import json
from unittest.mock import MagicMock, patch

from opscopilot_agent_runtime.llm.base import _node_span_name
from opscopilot_agent_runtime.llm.planner import LlmPlanner
from opscopilot_agent_runtime.persistence import AgentRunRecorder
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


def _mock_litellm_response(payload: dict):
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = json.dumps(payload)
    resp.usage = MagicMock()
    resp.usage.prompt_tokens = 10
    resp.usage.completion_tokens = 5
    resp._hidden_params = {"response_cost": 0.001}
    resp.model = "model"
    return resp


def _planner(recorder: AgentRunRecorder | None = None):
    provider = BedrockProvider()
    budget = BudgetEnforcer(BudgetState(max_usd=1.0, total_usd=0.0))
    ledger = CostLedger()
    return LlmPlanner(
        provider=provider,
        model_id="anthropic.claude-3-sonnet",
        budget=budget,
        ledger=ledger,
        recorder=recorder,
    )


def test_llm_planner_builds_plan():
    payload = {"steps": [{"tool_name": "k8s.list_pods"}]}
    with patch("litellm.completion", return_value=_mock_litellm_response(payload)):
        planner = _planner()
        plan = planner.plan("check pods", [{"name": "k8s.list_pods", "description": "List pods"}])

    assert plan.steps[0].tool_name == "k8s.list_pods"
    assert plan.steps[0].args == {}


def test_llm_planner_deduplicates_tools():
    payload = {"steps": [{"tool_name": "k8s.list_pods"}, {"tool_name": "k8s.list_pods"}]}
    with patch("litellm.completion", return_value=_mock_litellm_response(payload)):
        planner = _planner()
        plan = planner.plan("check pods", [{"name": "k8s.list_pods", "description": "List pods"}])

    assert len(plan.steps) == 1


def test_llm_planner_records_calls():
    payload = {"steps": [{"tool_name": "k8s.list_pods"}]}
    recorder = FakeRecorder()
    with patch("litellm.completion", return_value=_mock_litellm_response(payload)):
        planner = _planner(recorder=recorder)
        planner.plan("check pods", [{"name": "k8s.list_pods", "description": "List pods"}])

    assert recorder.llm_calls == 1
    assert recorder.budget_events == 1


def test_node_span_name_includes_agent_node():
    assert _node_span_name("planner") == "llm.node.planner"
    assert _node_span_name("clarifier question") == "llm.node.clarifier_question"
