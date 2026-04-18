import json
from unittest.mock import MagicMock, patch

from opscopilot_agent_runtime.llm.clarifier import LlmClarifier
from opscopilot_agent_runtime.llm.planner import LlmPlanner
from opscopilot_agent_runtime.llm.scope import ScopeClassifier
from opscopilot_agent_runtime.nodes.planner_node import Plan, PlanStep
from opscopilot_agent_runtime.state import AgentState
from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer, BudgetState
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider


class FakePromptSource:
    def __init__(self):
        self.prompts = {
            "planner": "Planner prompt from source.",
            "scope": "Scope prompt from source.",
            "clarifier": "Clarifier prompt from source.",
            "clarifier_question": "Clarifier question prompt from source.",
        }

    def get(self, name: str, version: str) -> str:
        assert version == "test"
        return self.prompts[name]


def _provider():
    return BedrockProvider()


def _budget():
    return BudgetEnforcer(BudgetState(max_usd=1.0, total_usd=0.0))


def _mock_litellm_json(payload: dict):
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = json.dumps(payload)
    resp.usage = MagicMock()
    resp.usage.prompt_tokens = 10
    resp.usage.completion_tokens = 5
    resp.usage.cache_read_input_tokens = 0
    resp._hidden_params = {"response_cost": 0.001}
    resp.model = "model"
    return resp


def _mock_litellm_text(text: str):
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = text
    resp.usage = MagicMock()
    resp.usage.prompt_tokens = 10
    resp.usage.completion_tokens = 5
    resp.usage.cache_read_input_tokens = 0
    resp._hidden_params = {"response_cost": 0.001}
    resp.model = "model"
    return resp


def test_planner_uses_prompt_source():
    planner = LlmPlanner(
        provider=_provider(),
        model_id="anthropic.claude-3-sonnet",
        budget=_budget(),
        ledger=CostLedger(),
        prompt_source=FakePromptSource(),
        prompt_version="test",
    )

    with patch("litellm.completion", return_value=_mock_litellm_json({"steps": []})) as completion:
        planner.plan("check pods", [{"name": "k8s.list_pods", "description": "List pods"}])

    assert completion.call_args.kwargs["messages"][0]["content"] == "Planner prompt from source."


def test_scope_classifier_uses_prompt_source():
    classifier = ScopeClassifier(
        provider=_provider(),
        model_id="anthropic.claude-3-sonnet",
        budget=_budget(),
        ledger=CostLedger(),
        prompt_source=FakePromptSource(),
        prompt_version="test",
    )

    with patch("litellm.completion", return_value=_mock_litellm_json({"allowed": True, "response": ""})) as completion:
        classifier.classify("list pods", ["k8s.list_pods: List pods in a namespace"])

    assert completion.call_args.kwargs["messages"][0]["content"] == "Scope prompt from source."



def test_scope_classifier_default_prompt_version_is_latest():
    classifier = ScopeClassifier(
        provider=_provider(),
        model_id="anthropic.claude-3-sonnet",
        budget=_budget(),
        ledger=CostLedger(),
    )
    assert classifier._prompt_version == "latest"


def test_clarifier_uses_prompt_source():
    clarifier = LlmClarifier(
        provider=_provider(),
        model_id="anthropic.claude-3-sonnet",
        budget=_budget(),
        ledger=CostLedger(),
        prompt_source=FakePromptSource(),
        prompt_version="test",
    )
    state = AgentState(
        prompt="list pods in default",
        plan=Plan(steps=[PlanStep(step_id="1", tool_name="k8s.list_pods", args={})]),
    )

    with patch("litellm.completion", return_value=_mock_litellm_json({"action": "proceed", "steps": []})) as completion:
        clarifier.clarify(state, [])

    assert completion.call_args.kwargs["messages"][0]["content"] == "Clarifier prompt from source."


def test_clarifier_question_uses_prompt_source():
    clarifier = LlmClarifier(
        provider=_provider(),
        model_id="anthropic.claude-3-sonnet",
        budget=_budget(),
        ledger=CostLedger(),
        prompt_source=FakePromptSource(),
        prompt_version="test",
    )

    with patch("litellm.completion", return_value=_mock_litellm_text("Which namespace?")) as completion:
        question = clarifier.generate_clarify_question("list pods", ["namespace"])

    assert question == "Which namespace?"
    assert completion.call_args.kwargs["messages"][0]["content"] == "Clarifier question prompt from source."
