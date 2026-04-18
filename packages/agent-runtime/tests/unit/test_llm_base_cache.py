from unittest.mock import MagicMock, patch

from opscopilot_agent_runtime.llm.injection_classifier import LlmInjectionClassifier
from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer, BudgetState
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider
from opscopilot_llm_gateway.types import LlmError, LlmOutput, LlmResponse


def _cache_hit_response() -> LlmResponse:
    return LlmResponse(
        output=LlmOutput(type="json", text=None, json={"is_injection": False}),
        error=None,
        tokens_input=10,
        tokens_output=2,
        cost_usd=0.0001,
        latency_ms=50,
        provider_metadata={"provider": "bedrock", "model": "test-model"},
        cache_hit=True,
        cache_read_input_tokens=8,
    )


def _cache_miss_response() -> LlmResponse:
    return LlmResponse(
        output=LlmOutput(type="json", text=None, json={"is_injection": False}),
        error=None,
        tokens_input=10,
        tokens_output=2,
        cost_usd=0.0001,
        latency_ms=50,
        provider_metadata={"provider": "bedrock", "model": "test-model"},
        cache_hit=False,
        cache_read_input_tokens=0,
    )


def _classifier():
    return LlmInjectionClassifier(
        provider=BedrockProvider(),
        model_id="test-model",
        budget=BudgetEnforcer(BudgetState(max_usd=1.0, total_usd=0.0)),
        ledger=CostLedger(),
        prompt_version="v1",
    )


def test_cache_hit_included_in_recorder_metadata():
    recorder = MagicMock()
    recorder.session_id = "s1"
    recorder.run_id = "r1"

    with patch("opscopilot_agent_runtime.llm.base.run_gateway_call", return_value=_cache_hit_response()):
        _classifier().classify("some prompt", recorder=recorder)

    _, kwargs = recorder.record_llm_call.call_args
    meta = kwargs["metadata_json"]
    assert meta["cache_hit"] is True
    assert meta["cache_read_input_tokens"] == 8
    assert meta["provider"] == "bedrock"


def test_cache_miss_included_in_recorder_metadata():
    recorder = MagicMock()
    recorder.session_id = "s1"
    recorder.run_id = "r1"

    with patch("opscopilot_agent_runtime.llm.base.run_gateway_call", return_value=_cache_miss_response()):
        _classifier().classify("some prompt", recorder=recorder)

    _, kwargs = recorder.record_llm_call.call_args
    meta = kwargs["metadata_json"]
    assert meta["cache_hit"] is False
    assert meta["cache_read_input_tokens"] == 0
