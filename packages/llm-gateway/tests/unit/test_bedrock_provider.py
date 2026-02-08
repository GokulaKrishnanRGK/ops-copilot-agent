from opscopilot_llm_gateway.providers.bedrock import BedrockProvider, BedrockResult
from opscopilot_llm_gateway.types import (
    LlmMessage,
    LlmRequest,
    LlmResponseFormat,
    LlmTags,
)


class FakeClient:
    def __init__(self, result: BedrockResult):
        self._result = result

    def invoke(self, request):
        return self._result


def _request():
    return LlmRequest(
        model_id="m1",
        messages=[LlmMessage(role="user", content="hi")],
        response_format=LlmResponseFormat(type="text", schema=None),
        temperature=0.0,
        max_tokens=10,
        idempotency_key="k",
        tags=LlmTags(session_id="s", agent_run_id="r", agent_node="planner"),
    )


def test_bedrock_provider_text():
    result = BedrockResult(
        output_text="ok",
        output_json=None,
        tokens_input=1,
        tokens_output=1,
        cost_usd=0.01,
        latency_ms=10,
        provider_metadata={"m": 1},
    )
    provider = BedrockProvider(FakeClient(result))
    response = provider.invoke(_request())
    assert response.output.type == "text"
    assert response.output.text == "ok"


def test_bedrock_provider_json():
    result = BedrockResult(
        output_text=None,
        output_json={"a": 1},
        tokens_input=1,
        tokens_output=1,
        cost_usd=0.01,
        latency_ms=10,
        provider_metadata={"m": 1},
    )
    provider = BedrockProvider(FakeClient(result))
    response = provider.invoke(_request())
    assert response.output.type == "json"
    assert response.output.json == {"a": 1}
