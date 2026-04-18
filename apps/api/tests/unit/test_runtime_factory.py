from opscopilot_api.config_cache import NodeConfig, RuntimeConfigData
from opscopilot_api.services.runtime_factory import SampledAnswerScorer, _build_answer_scorer


def _make_config(**overrides) -> RuntimeConfigData:
    defaults = dict(
        id="test",
        schema_version="v1",
        nodes={
            "scope": NodeConfig(model_id="m", prompt_version="latest"),
            "planner": NodeConfig(model_id="m", prompt_version="latest"),
            "clarifier": NodeConfig(model_id="m", prompt_version="latest"),
            "answer": NodeConfig(model_id="m", prompt_version="latest"),
            "summarizer": NodeConfig(model_id="m", prompt_version="latest"),
            "injection_classifier": NodeConfig(model_id="m", prompt_version="latest"),
        },
        max_agent_steps=10,
        max_budget_usd=None,
    )
    defaults.update(overrides)
    return RuntimeConfigData(**defaults)


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
    monkeypatch.setenv("LANGFUSE_HOST", "http://langfuse.local")
    config = _make_config(eval_sample_rate=0.0)

    scorer = _build_answer_scorer(config, provider=None, budget=None, ledger=None)

    assert scorer is None
