"""
Integration tests verifying that cache_control annotations on LlmMessage are correctly
translated to Bedrock Converse API wire format (cachePoint blocks).
These tests call into LiteLLM's internal transformer to confirm the full translation chain.
"""
import json

from litellm.llms.bedrock.chat.converse_transformation import (
    UNSUPPORTED_BEDROCK_CONVERSE_BETA_PATTERNS,
    AmazonConverseConfig,
)
from litellm.litellm_core_utils.prompt_templates.factory import _bedrock_converse_messages_pt

from opscopilot_llm_gateway.providers.bedrock import _build_messages
from opscopilot_llm_gateway.types import LlmMessage, LlmRequest, LlmResponseFormat, LlmTags


def _request(messages: list) -> LlmRequest:
    return LlmRequest(
        model_id="anthropic.claude-3-sonnet",
        messages=messages,
        response_format=LlmResponseFormat(type="text", schema=None),
        temperature=0.0,
        max_tokens=10,
        idempotency_key="k",
        tags=LlmTags(session_id="s", agent_run_id="r", agent_node="test"),
    )


def test_system_cache_control_produces_cache_point_block():
    req = _request([
        LlmMessage(role="system", content="You are helpful", cache_control={"type": "ephemeral"}),
        LlmMessage(role="user", content="hi"),
    ])
    raw = _build_messages(req)
    _, system_blocks = AmazonConverseConfig()._transform_system_message(list(raw))

    text_blocks = [b for b in system_blocks if "text" in b]
    cache_blocks = [b for b in system_blocks if "cachePoint" in b]
    assert len(text_blocks) == 1
    assert text_blocks[0]["text"] == "You are helpful"
    assert len(cache_blocks) == 1
    assert cache_blocks[0]["cachePoint"]["type"] == "default"


def test_system_without_cache_control_produces_no_cache_point():
    req = _request([
        LlmMessage(role="system", content="You are helpful"),
        LlmMessage(role="user", content="hi"),
    ])
    raw = _build_messages(req)
    _, system_blocks = AmazonConverseConfig()._transform_system_message(list(raw))

    cache_blocks = [b for b in system_blocks if "cachePoint" in b]
    assert len(cache_blocks) == 0
    assert system_blocks[0]["text"] == "You are helpful"


def test_user_list_content_cache_control_produces_cache_point_in_content_blocks():
    tools = [{"name": "k8s.list_pods", "description": "List pods"}]
    req = _request([
        LlmMessage(role="system", content="sys"),
        LlmMessage(
            role="user",
            content=[
                {"type": "text", "text": json.dumps({"tools": tools}), "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": json.dumps({"prompt": "check pods"})},
            ],
        ),
    ])
    raw = _build_messages(req)
    remaining, _ = AmazonConverseConfig()._transform_system_message(list(raw))
    bedrock_messages = _bedrock_converse_messages_pt(
        messages=remaining,
        model="anthropic.claude-3-sonnet",
        llm_provider="bedrock_converse",
    )

    user_msg = next(m for m in bedrock_messages if m["role"] == "user")
    content_blocks = user_msg["content"]
    cache_point_blocks = [b for b in content_blocks if "cachePoint" in b]
    assert len(cache_point_blocks) >= 1, "expected at least one cachePoint block in user content"
    assert cache_point_blocks[0]["cachePoint"]["type"] == "default"


def test_prompt_caching_beta_header_not_forwarded_to_bedrock():
    assert "prompt-caching" in UNSUPPORTED_BEDROCK_CONVERSE_BETA_PATTERNS
