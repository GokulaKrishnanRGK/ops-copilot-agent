import pytest

from opscopilot_api.services.runtime_factory import SampledAnswerScorer, _build_answer_scorer, _read_sample_rate


def test_read_sample_rate_defaults_to_ten_percent(monkeypatch):
    monkeypatch.delenv("EVAL_SAMPLE_RATE", raising=False)

    assert _read_sample_rate() == 0.1


def test_read_sample_rate_rejects_invalid_values(monkeypatch):
    monkeypatch.setenv("EVAL_SAMPLE_RATE", "1.5")

    with pytest.raises(RuntimeError, match="between 0 and 1"):
        _read_sample_rate()


def test_sampled_answer_scorer_skips_when_random_value_exceeds_rate():
    calls = []
    scorer = SampledAnswerScorer(calls.append, sample_rate=0.25, random_value=lambda: 0.5)

    scorer("state")

    assert calls == []


def test_sampled_answer_scorer_invokes_when_random_value_is_under_rate():
    calls = []
    scorer = SampledAnswerScorer(calls.append, sample_rate=0.25, random_value=lambda: 0.1)

    scorer("state")

    assert calls == ["state"]


def test_build_answer_scorer_disables_sampling_at_zero(monkeypatch):
    monkeypatch.setenv("EVAL_SAMPLE_RATE", "0")
    monkeypatch.setenv("LANGFUSE_HOST", "http://langfuse.local")

    scorer = _build_answer_scorer(provider=None, budget=None, ledger=None)

    assert scorer is None
