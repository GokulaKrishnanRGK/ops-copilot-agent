import json
from unittest.mock import MagicMock, patch

from opscopilot_agent_runtime.llm.answer import AnswerSynthesizer
from opscopilot_agent_runtime.nodes.answer_node import AnswerNode
from opscopilot_agent_runtime.nodes.tool_executor_node import ToolResult
from opscopilot_agent_runtime.state import AgentState
from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer, BudgetState
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider


def _mock_litellm_response(content: str):
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = content
    resp.usage = MagicMock()
    resp.usage.prompt_tokens = 10
    resp.usage.completion_tokens = 5
    resp.usage.cache_read_input_tokens = 0
    resp._hidden_params = {"response_cost": 0.001}
    resp.model = "model"
    return resp


def _node():
    provider = BedrockProvider()
    synthesizer = AnswerSynthesizer(
        provider=provider,
        model_id="anthropic.claude-3-sonnet",
        budget=BudgetEnforcer(BudgetState(max_usd=1.0, total_usd=0.0)),
        ledger=CostLedger(),
        prompt_version="v1",
    )
    return AnswerNode(synthesizer)


def test_answer_node():
    with patch("litellm.completion", return_value=_mock_litellm_response(json.dumps({"answer": "ok"}))):
        node = _node()
        state = AgentState(
            prompt="status",
            tool_results=[ToolResult(step_id="1", tool_name="k8s.list_pods", result={})],
        )
        result = node(state)
    assert result.answer == "ok"
