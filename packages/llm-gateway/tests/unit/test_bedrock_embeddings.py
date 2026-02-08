from opscopilot_llm_gateway.providers.bedrock_embeddings import (
    BedrockEmbeddingClient,
    BedrockEmbeddingProvider,
)
from opscopilot_llm_gateway.types import EmbeddingRequest, LlmTags


class FakeRuntime:
    def invoke_model(self, modelId, body):
        class FakeBody:
            def read(self):
                return b'{"embedding": [0.1, 0.2]}'

        return {"body": FakeBody()}


def test_bedrock_embedding_provider_embeds():
    client = BedrockEmbeddingClient(client=FakeRuntime())
    provider = BedrockEmbeddingProvider(client=client)
    request = EmbeddingRequest(
        model_id="model",
        texts=["hello"],
        idempotency_key="id",
        tags=LlmTags(session_id="s", agent_run_id="r", agent_node="n"),
    )
    response = provider.embed(request)
    assert response.vectors == [[0.1, 0.2]]
