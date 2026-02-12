from opscopilot_agent_runtime.nodes.answer_node import AnswerNode
from opscopilot_agent_runtime.llm.answer import AnswerSynthesizer
from opscopilot_agent_runtime.nodes.tool_executor_node import ToolResult
from opscopilot_agent_runtime.state import AgentState
from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer, BudgetState
from opscopilot_llm_gateway.costs import CostEntry
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider, BedrockResult


def _node():
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
    synthesizer = AnswerSynthesizer(
        provider=provider,
        model_id="model",
        cost_table={"model": CostEntry(model_id="model", input_per_1k=0.0, output_per_1k=0.0)},
        budget=BudgetEnforcer(BudgetState(max_usd=1.0, total_usd=0.0)),
        ledger=CostLedger(),
    )
    return AnswerNode(synthesizer)


def test_answer_node():
    node = _node()
    state = AgentState(
        prompt="status",
        tool_results=[ToolResult(step_id="1", tool_name="k8s.list_pods", result={})],
    )
    result = node(state)
    assert result.answer == "ok"
