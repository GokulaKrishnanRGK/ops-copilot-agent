from unittest.mock import MagicMock, patch

from opscopilot_llm_gateway.providers.bedrock import BedrockProvider
from opscopilot_llm_gateway.types import (
    LlmMessage,
    LlmRequest,
    LlmResponseFormat,
    LlmTags,
)


def _request(response_type="text"):
    return LlmRequest(
        model_id="anthropic.claude-3-sonnet",
        messages=[LlmMessage(role="user", content="hi")],
        response_format=LlmResponseFormat(type=response_type, schema=None),
        temperature=0.0,
        max_tokens=10,
        idempotency_key="k",
        tags=LlmTags(session_id="s", agent_run_id="r", agent_node="planner"),
    )


def _mock_litellm_response(content="ok", tokens_in=10, tokens_out=5, cost=0.001):
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = content
    resp.usage = MagicMock()
    resp.usage.prompt_tokens = tokens_in
    resp.usage.completion_tokens = tokens_out
    resp._hidden_params = {"response_cost": cost}
    resp.model = "anthropic.claude-3-sonnet"
    return resp


def test_bedrock_provider_text():
    with patch("litellm.completion", return_value=_mock_litellm_response("hello")) as mock_completion:
        provider = BedrockProvider()
        response = provider.invoke(_request())

    mock_completion.assert_called_once()
    call_kwargs = mock_completion.call_args.kwargs
    assert call_kwargs["model"] == "bedrock/anthropic.claude-3-sonnet"
    assert call_kwargs["stream"] is False
    assert response.output.type == "text"
    assert response.output.text == "hello"
    assert response.tokens_input == 10
    assert response.tokens_output == 5
    assert response.cost_usd == 0.001
    assert response.provider_metadata == {
        "provider": "bedrock",
        "model": "anthropic.claude-3-sonnet",
    }


def test_bedrock_provider_json_schema():
    with patch("litellm.completion", return_value=_mock_litellm_response('{"key": "val"}')):
        provider = BedrockProvider()
        request = LlmRequest(
            model_id="m",
            messages=[LlmMessage(role="user", content="hi")],
            response_format=LlmResponseFormat(type="json_schema", schema={"type": "object"}),
            temperature=0.0,
            max_tokens=10,
            idempotency_key="k",
            tags=LlmTags(session_id="s", agent_run_id="r", agent_node="planner"),
        )
        response = provider.invoke(request)

    assert response.output.type == "json"
    assert response.output.json == {"key": "val"}


def test_bedrock_provider_already_prefixed():
    with patch("litellm.completion", return_value=_mock_litellm_response()) as mock_completion:
        provider = BedrockProvider()
        request = LlmRequest(
            model_id="bedrock/already-prefixed",
            messages=[LlmMessage(role="user", content="hi")],
            response_format=LlmResponseFormat(type="text", schema=None),
            temperature=0.0,
            max_tokens=10,
            idempotency_key="k",
            tags=LlmTags(session_id="s", agent_run_id="r", agent_node="p"),
        )
        provider.invoke(request)

    assert mock_completion.call_args.kwargs["model"] == "bedrock/already-prefixed"


def test_bedrock_provider_stream():
    chunk1 = MagicMock()
    chunk1.choices = [MagicMock()]
    chunk1.choices[0].delta.content = "hello "
    chunk1.usage = None

    chunk2 = MagicMock()
    chunk2.choices = [MagicMock()]
    chunk2.choices[0].delta.content = "world"
    chunk2.usage = MagicMock()
    chunk2.usage.prompt_tokens = 8
    chunk2.usage.completion_tokens = 3

    with patch("litellm.completion", return_value=iter([chunk1, chunk2])):
        with patch("litellm.completion_cost", return_value=0.0005):
            provider = BedrockProvider()
            deltas: list[str] = []
            response = provider.invoke_stream(_request(), on_delta=deltas.append)

    assert "".join(deltas) == "hello world"
    assert response.output.text == "hello world"
    assert response.tokens_input == 8
    assert response.tokens_output == 3
    assert response.cost_usd == 0.0005
    assert response.provider_metadata == {
        "provider": "bedrock",
        "model": "anthropic.claude-3-sonnet",
    }
