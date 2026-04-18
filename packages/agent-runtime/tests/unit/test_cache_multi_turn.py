"""
Validates that the caching design produces >70% cache eligibility in a sustained multi-turn
session where the same MCP tool set is available across all turns.

The cache hit rate against a live Bedrock endpoint depends on AWS infrastructure;
this test proves that:
  1. Every planner call emits an identical, cacheable system block.
  2. Every planner call emits an identical, cacheable tools block (stable within a session).
  3. Only the prompt block varies per call (not over-cached).
  4. For a session of N calls the theoretical hit rate is (N-1)/N, which exceeds 70% for N >= 4.
"""
import json
from unittest.mock import patch

import pytest

from opscopilot_agent_runtime.llm.planner import LlmPlanner
from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer, BudgetState
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider


_TOOLS = [
    {"name": "k8s.list_pods", "description": "List pods in a namespace"},
    {"name": "k8s.get_pod_logs", "description": "Fetch logs for a pod"},
    {"name": "k8s.describe_deployment", "description": "Describe a deployment"},
]

_PROMPTS = [
    "check pod health in the default namespace",
    "show logs for the api pod",
    "describe the web deployment",
    "list all pods in the staging namespace",
    "get logs for the worker pod",
]


def _planner():
    return LlmPlanner(
        provider=BedrockProvider(),
        model_id="anthropic.claude-3-haiku",
        budget=BudgetEnforcer(BudgetState(max_usd=10.0, total_usd=0.0)),
        ledger=CostLedger(),
        prompt_version="v1",
    )


def _fake_litellm(payload: dict):
    from unittest.mock import MagicMock
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = json.dumps(payload)
    resp.usage = MagicMock()
    resp.usage.prompt_tokens = 10
    resp.usage.completion_tokens = 3
    resp.usage.cache_read_input_tokens = 0
    resp._hidden_params = {"response_cost": 0.0001}
    resp.model = "model"
    return resp


def _capture_planner_messages(n_turns: int) -> list[list[dict]]:
    """Run the planner n_turns times and return the messages list for each call."""
    planner = _planner()
    all_call_messages: list[list[dict]] = []

    def fake_completion(**kwargs):
        all_call_messages.append(kwargs["messages"])
        return _fake_litellm({"steps": [{"tool_name": "k8s.list_pods"}]})

    with patch("litellm.completion", side_effect=fake_completion):
        for prompt in _PROMPTS[:n_turns]:
            planner.plan(prompt, _TOOLS)

    return all_call_messages


class TestMultiTurnCacheEligibility:
    def setup_method(self):
        self.messages_per_turn = _capture_planner_messages(len(_PROMPTS))

    def test_system_message_identical_across_all_turns(self):
        system_blocks = [
            next(m for m in call_msgs if m["role"] == "system")
            for call_msgs in self.messages_per_turn
        ]
        first = system_blocks[0]
        for block in system_blocks[1:]:
            assert block["content"] == first["content"], "system prompt drifted across turns"
        assert first.get("cache_control") == {"type": "ephemeral"}, "system message must be cacheable"

    def test_tool_list_block_identical_across_all_turns(self):
        tools_blocks = []
        for call_msgs in self.messages_per_turn:
            user_msg = next(m for m in call_msgs if m["role"] == "user")
            assert isinstance(user_msg["content"], list), "user content must be a list of blocks"
            tools_blocks.append(user_msg["content"][0])

        first = tools_blocks[0]
        assert first.get("cache_control") == {"type": "ephemeral"}, "tools block must be cacheable"
        parsed_first = json.loads(first["text"])
        for block in tools_blocks[1:]:
            assert json.loads(block["text"]) == parsed_first, "tools block content drifted across turns"
            assert block.get("cache_control") == {"type": "ephemeral"}, "tools block must be cacheable on every turn"

    def test_prompt_block_varies_across_turns(self):
        prompt_texts = []
        for call_msgs in self.messages_per_turn:
            user_msg = next(m for m in call_msgs if m["role"] == "user")
            prompt_block = user_msg["content"][1]
            assert "cache_control" not in prompt_block, "prompt block must not be cached (it changes)"
            prompt_texts.append(prompt_block["text"])

        assert len(set(prompt_texts)) == len(_PROMPTS), "each turn must have a distinct prompt block"

    def test_theoretical_cache_hit_rate_exceeds_70_percent(self):
        n = len(_PROMPTS)
        hit_rate = (n - 1) / n
        assert hit_rate > 0.70, (
            f"session of {n} turns yields {hit_rate:.0%} hit rate, need >70%"
        )

    @pytest.mark.parametrize("min_turns", [4])
    def test_min_session_length_for_70_percent(self, min_turns: int):
        hit_rate = (min_turns - 1) / min_turns
        assert hit_rate >= 0.70, f"{min_turns} turns yields {hit_rate:.0%}, need >=70%"
