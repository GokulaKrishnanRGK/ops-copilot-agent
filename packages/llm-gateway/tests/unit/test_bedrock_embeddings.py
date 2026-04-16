from unittest.mock import MagicMock, patch

from opscopilot_llm_gateway.providers.bedrock_embeddings import BedrockEmbeddingProvider
from opscopilot_llm_gateway.types import EmbeddingRequest, LlmTags


def _request(model_id="amazon.titan-embed-text-v1"):
    return EmbeddingRequest(
        model_id=model_id,
        texts=["hello", "world"],
        idempotency_key="id",
        tags=LlmTags(session_id="s", agent_run_id="r", agent_node="n"),
    )


def _mock_litellm_embedding(vectors=None):
    resp = MagicMock()
    resp.data = [{"embedding": v} for v in (vectors or [[0.1, 0.2], [0.3, 0.4]])]
    resp.usage = MagicMock()
    resp.usage.total_tokens = 10
    resp._hidden_params = {"response_cost": 0.0002}
    return resp


def test_bedrock_embedding_provider_embeds():
    with patch("litellm.embedding", return_value=_mock_litellm_embedding()) as mock_embed:
        provider = BedrockEmbeddingProvider()
        response = provider.embed(_request())

    mock_embed.assert_called_once()
    assert mock_embed.call_args.kwargs["model"] == "bedrock/amazon.titan-embed-text-v1"
    assert response.vectors == [[0.1, 0.2], [0.3, 0.4]]
    assert response.tokens_input == 10
    assert response.cost_usd == 0.0002


def test_bedrock_embedding_already_prefixed():
    with patch("litellm.embedding", return_value=_mock_litellm_embedding()) as mock_embed:
        provider = BedrockEmbeddingProvider()
        provider.embed(_request(model_id="bedrock/already-prefixed"))

    assert mock_embed.call_args.kwargs["model"] == "bedrock/already-prefixed"
