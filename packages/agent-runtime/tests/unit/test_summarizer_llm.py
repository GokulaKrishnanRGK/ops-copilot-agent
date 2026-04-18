from unittest.mock import MagicMock, patch

from opscopilot_agent_runtime.llm.summarizer import SummarizerLlmNode
from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer, BudgetState
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider
from opscopilot_llm_gateway.types import LlmError, LlmOutput, LlmResponse


def _ok_response(text: str) -> LlmResponse:
    return LlmResponse(
        output=LlmOutput(type="text", text=text, json=None),
        error=None,
        tokens_input=50,
        tokens_output=20,
        cost_usd=0.0001,
        latency_ms=100,
        provider_metadata={"provider": "bedrock", "model": "haiku"},
        cache_hit=False,
        cache_read_input_tokens=0,
    )


def _error_response() -> LlmResponse:
    return LlmResponse(
        output=LlmOutput(type="text", text=None, json=None),
        error=LlmError(error_type="timeout", message="timeout"),
        tokens_input=0,
        tokens_output=0,
        cost_usd=0.0,
        latency_ms=0,
        provider_metadata={},
        cache_hit=False,
        cache_read_input_tokens=0,
    )


def _node() -> SummarizerLlmNode:
    return SummarizerLlmNode(
        provider=BedrockProvider(),
        model_id="test-model",
        budget=BudgetEnforcer(BudgetState(max_usd=10.0, total_usd=0.0)),
        ledger=CostLedger(),
        prompt_version="v1",
    )


def test_summarize_returns_text_from_response():
    with patch("opscopilot_agent_runtime.llm.base.run_gateway_call", return_value=_ok_response("  summary output  ")):
        result = _node().summarize(older_turns=["turn1", "turn2"])
    assert result == "summary output"


def test_summarize_includes_existing_summary_in_request():
    captured_requests: list = []

    def fake_run_gateway_call(provider, request, budget, ledger, on_delta=None):
        captured_requests.append(request)
        return _ok_response("new summary")

    with patch("opscopilot_agent_runtime.llm.base.run_gateway_call", side_effect=fake_run_gateway_call):
        _node().summarize(
            older_turns=["turn1"],
            existing_summary="previous summary",
        )

    assert len(captured_requests) == 1
    req = captured_requests[0]
    user_msg = next(m for m in req.messages if m.role == "user")
    content = user_msg.content if isinstance(user_msg.content, str) else ""
    assert "previous summary" in content or "PREVIOUS SUMMARY" in content


def test_summarize_returns_existing_summary_on_error():
    with patch("opscopilot_agent_runtime.llm.base.run_gateway_call", return_value=_error_response()):
        result = _node().summarize(
            older_turns=["turn1"],
            existing_summary="fallback",
        )
    assert result == "fallback"


def test_summarize_returns_empty_string_on_error_with_no_existing():
    with patch("opscopilot_agent_runtime.llm.base.run_gateway_call", return_value=_error_response()):
        result = _node().summarize(older_turns=["turn1"])
    assert result == ""


def test_summarize_includes_log_excerpts():
    captured_requests: list = []

    def fake_run_gateway_call(provider, request, budget, ledger, on_delta=None):
        captured_requests.append(request)
        return _ok_response("summary with logs")

    with patch("opscopilot_agent_runtime.llm.base.run_gateway_call", side_effect=fake_run_gateway_call):
        _node().summarize(
            older_turns=["turn1"],
            log_excerpts=["Error: OOMKilled", "Fatal: crashloop"],
        )

    req = captured_requests[0]
    user_msg = next(m for m in req.messages if m.role == "user")
    content = user_msg.content if isinstance(user_msg.content, str) else ""
    assert "OOMKilled" in content or "LOG EXCERPTS" in content
