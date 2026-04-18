import pytest

from opscopilot_agent_runtime.history import HistoryManager, InMemorySummaryStore


class TestHistoryManagerCondense:
    def test_no_split_when_history_shorter_than_window(self):
        recent, older = HistoryManager.condense(["a", "b", "c"], window=6)
        assert recent == ["a", "b", "c"]
        assert older == []

    def test_no_split_when_history_equals_window(self):
        history = ["a", "b", "c", "d", "e", "f"]
        recent, older = HistoryManager.condense(history, window=6)
        assert recent == history
        assert older == []

    def test_split_when_history_exceeds_window(self):
        history = ["t1", "t2", "t3", "t4", "t5", "t6", "t7"]
        recent, older = HistoryManager.condense(history, window=4)
        assert recent == ["t4", "t5", "t6", "t7"]
        assert older == ["t1", "t2", "t3"]

    def test_window_zero_returns_all_as_recent(self):
        recent, older = HistoryManager.condense(["a", "b"], window=0)
        assert recent == ["a", "b"]
        assert older == []

    def test_empty_history(self):
        recent, older = HistoryManager.condense([], window=6)
        assert recent == []
        assert older == []

    def test_does_not_mutate_input(self):
        history = ["x", "y", "z"]
        HistoryManager.condense(history, window=2)
        assert history == ["x", "y", "z"]


class TestInMemorySummaryStore:
    def test_load_missing_returns_none(self):
        store = InMemorySummaryStore()
        assert store.load("session-1") is None

    def test_save_and_load(self):
        store = InMemorySummaryStore()
        store.save("session-1", "summary text")
        assert store.load("session-1") == "summary text"

    def test_save_overwrites_previous(self):
        store = InMemorySummaryStore()
        store.save("session-1", "first")
        store.save("session-1", "second")
        assert store.load("session-1") == "second"

    def test_independent_sessions(self):
        store = InMemorySummaryStore()
        store.save("s1", "a")
        store.save("s2", "b")
        assert store.load("s1") == "a"
        assert store.load("s2") == "b"
