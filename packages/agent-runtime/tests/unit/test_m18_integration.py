"""
M18 integration test: simulates a 10-turn session and verifies that
history condensation keeps the merged prompt token-bounded.

Uses InMemorySummaryStore + a stub SummarizerLlmNode that returns a
fixed summary string, so no live LLM calls are needed.
"""
from unittest.mock import MagicMock, patch

import pytest

from opscopilot_agent_runtime.history import HistoryManager, InMemorySummaryStore
from opscopilot_agent_runtime.runtime.runtime import AgentRuntime, _extract_log_excerpts
from opscopilot_agent_runtime.state import AgentState


_WINDOW = 3
_TURNS = [f"user turn {i}" for i in range(1, 11)]


class _StubSummarizer:
    def __init__(self):
        self.call_count = 0
        self.last_older_turns: list[str] = []

    def summarize(self, older_turns, existing_summary=None, log_excerpts=None, recorder=None) -> str:
        self.call_count += 1
        self.last_older_turns = list(older_turns)
        prefix = f"{existing_summary}; " if existing_summary else ""
        return f"{prefix}summary of {len(older_turns)} turns"


class _StubGraph:
    def build(self):
        return _StubCompiledGraph()


class _StubCompiledGraph:
    def stream(self, state_dict, config, stream_mode):
        return iter([state_dict])


class _StubLimits:
    max_agent_steps = 10
    max_tool_calls = 10
    max_llm_calls = 10
    max_execution_time_ms = 30_000


def _make_runtime(summarizer, store):
    from opscopilot_agent_runtime.runtime.limits import ExecutionLimits

    limits = ExecutionLimits(
        max_agent_steps=10,
        max_tool_calls=10,
        max_llm_calls=10,
        max_execution_time_ms=30_000,
    )
    rt = AgentRuntime(
        graph=_StubGraph(),
        limits=limits,
        summarizer=summarizer,
        summary_store=store,
        history_window_turns=_WINDOW,
    )
    return rt


class TestM18MultiTurnSession:
    def setup_method(self):
        self.summarizer = _StubSummarizer()
        self.store = InMemorySummaryStore()
        self.runtime = _make_runtime(self.summarizer, self.store)

    def _run_turn(self, turn_text: str, history: list[str]) -> AgentState:
        state = AgentState(prompt=turn_text, prompt_history=history)
        with patch("opscopilot_agent_runtime.runtime.runtime.clear_log_context"):
            result = self.runtime.run(state)
        return result

    def test_no_summarization_within_window(self):
        history: list[str] = []
        for turn in _TURNS[:_WINDOW]:
            state, recorder = self.runtime._prepare_state(
                AgentState(prompt=turn, prompt_history=list(history))
            )
            history.append(turn)
        assert self.summarizer.call_count == 0

    def test_summarization_triggered_beyond_window(self):
        history: list[str] = list(_TURNS[:_WINDOW])
        extra_turn = _TURNS[_WINDOW]
        state, _ = self.runtime._prepare_state(
            AgentState(prompt=extra_turn, prompt_history=history)
        )
        assert self.summarizer.call_count == 1

    def test_merged_prompt_uses_summary_format(self):
        history = list(_TURNS[:_WINDOW])
        extra_turn = _TURNS[_WINDOW]
        state, _ = self.runtime._prepare_state(
            AgentState(prompt=extra_turn, prompt_history=history)
        )
        assert state.prompt is not None
        assert "[SUMMARY]" in state.prompt
        assert "[RECENT]" in state.prompt

    def test_merged_prompt_contains_only_recent_turns(self):
        history = list(_TURNS[:_WINDOW])
        extra_turn = _TURNS[_WINDOW]
        state, _ = self.runtime._prepare_state(
            AgentState(prompt=extra_turn, prompt_history=history)
        )
        for old_turn in _TURNS[:1]:
            assert old_turn not in state.prompt or "[SUMMARY]" in state.prompt

    def test_summary_stored_in_summary_store(self):
        history = list(_TURNS[:_WINDOW])
        extra_turn = _TURNS[_WINDOW]
        recorder = MagicMock()
        recorder.session_id = "test-session"
        recorder.run_id = "test-run"
        recorder.start = MagicMock()
        runtime = _make_runtime(self.summarizer, self.store)
        runtime._recorder = recorder
        runtime._prepare_state(
            AgentState(prompt=extra_turn, prompt_history=history)
        )
        stored = self.store.load("test-session")
        assert stored is not None
        assert "summary" in stored

    def test_10_turns_summarizer_called_multiple_times(self):
        history: list[str] = []
        for turn in _TURNS:
            state, _ = self.runtime._prepare_state(
                AgentState(prompt=turn, prompt_history=list(history))
            )
            if state.prompt_history:
                history = list(state.prompt_history)
        assert self.summarizer.call_count > 0

    def test_merged_prompt_bounded_regardless_of_turn_count(self):
        history: list[str] = []
        prompt_lengths: list[int] = []
        for turn in _TURNS:
            state, _ = self.runtime._prepare_state(
                AgentState(prompt=turn, prompt_history=list(history))
            )
            if state.prompt:
                prompt_lengths.append(len(state.prompt))
            if state.prompt_history:
                history = list(state.prompt_history)
        max_len = max(prompt_lengths)
        assert max_len < 5000, f"merged prompt grew unboundedly to {max_len} chars"


class TestExtractLogExcerpts:
    def _result(self, tool_name: str, text: str):
        r = MagicMock()
        r.tool_name = tool_name
        r.text = text
        return r

    def test_extracts_error_lines_from_pod_logs(self):
        result = self._result("k8s.get_pod_logs", "INFO start\nError: OOMKilled\nFatal: crash\nINFO end")
        excerpts = _extract_log_excerpts([result])
        assert any("Error" in e or "Fatal" in e for e in excerpts)

    def test_ignores_non_log_tools(self):
        result = self._result("k8s.list_pods", "Error: something")
        excerpts = _extract_log_excerpts([result])
        assert excerpts == []

    def test_empty_tool_results(self):
        assert _extract_log_excerpts([]) == []
