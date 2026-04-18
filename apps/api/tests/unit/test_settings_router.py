from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from opscopilot_api.config_cache import NodeConfig, RuntimeConfigData
from opscopilot_db import models
from opscopilot_db.repositories.sqlalchemy import RuntimeConfigRepo

# ── shared helpers ─────────────────────────────────────────────────────────

_NODE_NAMES = ("scope", "planner", "clarifier", "answer", "summarizer", "injection_classifier")


def _all_nodes(model_id: str = "test-model", prompt_version: str = "latest") -> dict:
    return {name: {"model_id": model_id, "prompt_version": prompt_version} for name in _NODE_NAMES}


def _valid_patch_payload(**overrides) -> dict:
    base: dict = {
        "nodes": _all_nodes(),
        "max_agent_steps": 10,
        "max_budget_usd": None,
        "history_window_turns": 6,
        "summarizer_prompt_version": "latest",
        "eval_sample_rate": 0.1,
        "eval_llm_judge_enabled": True,
        "eval_ragas_enabled": True,
        "eval_judge_model_id": "anthropic.claude-3-haiku-20240307-v1:0",
        "prompt_injection_llm_check": False,
        "agent_max_tool_calls": 10,
        "agent_max_llm_calls": 10,
        "agent_max_execution_time_ms": 30000,
        "bedrock_embedding_model_id": "amazon.titan-embed-text-v1",
    }
    base.update(overrides)
    return base


def _make_config(**overrides) -> RuntimeConfigData:
    defaults: dict = {
        "id": "aabbccdd-0000-0000-0000-000000000001",
        "schema_version": "v1",
        "nodes": {name: NodeConfig(model_id="test-model", prompt_version="latest") for name in _NODE_NAMES},
        "max_agent_steps": 10,
        "max_budget_usd": None,
        "bedrock_embedding_model_id": "amazon.titan-embed-text-v1",
    }
    defaults.update(overrides)
    return RuntimeConfigData(**defaults)


def _make_db_row(config_json: dict, schema_version: str = "v1") -> models.RuntimeConfig:
    now = datetime.now(timezone.utc)
    return models.RuntimeConfig(
        id="row-id",
        schema_version=schema_version,
        config_json=config_json,
        created_at=now,
        updated_at=now,
    )


class _FakeConfigCache:
    def __init__(self, config: RuntimeConfigData) -> None:
        self._config = config

    def get(self) -> RuntimeConfigData:
        return self._config

    def set(self, config: RuntimeConfigData) -> None:
        self._config = config


# ── GET /api/settings ──────────────────────────────────────────────────────

def test_get_settings_returns_full_shape(app: object, client: TestClient) -> None:
    config = _make_config(
        eval_sample_rate=0.25,
        prompt_injection_llm_check=True,
        agent_max_tool_calls=20,
        agent_max_execution_time_ms=60_000,
    )
    app.state.config_cache = _FakeConfigCache(config)

    resp = client.get("/api/settings")

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == config.id
    assert data["schema_version"] == "v1"
    assert data["max_agent_steps"] == 10
    assert data["nodes"]["scope"]["model_id"] == "test-model"
    assert data["nodes"]["injection_classifier"]["prompt_version"] == "latest"
    assert data["eval_sample_rate"] == pytest.approx(0.25)
    assert data["prompt_injection_llm_check"] is True
    assert data["agent_max_tool_calls"] == 20
    assert data["agent_max_execution_time_ms"] == 60_000


def test_get_settings_nullable_budget(app: object, client: TestClient) -> None:
    app.state.config_cache = _FakeConfigCache(_make_config(max_budget_usd=None))

    resp = client.get("/api/settings")

    assert resp.status_code == 200
    assert resp.json()["max_budget_usd"] is None


# ── PATCH /api/settings — valid payloads ──────────────────────────────────

def test_patch_settings_returns_updated_values(app: object, client: TestClient) -> None:
    app.state.config_cache = _FakeConfigCache(_make_config())
    payload = _valid_patch_payload(max_agent_steps=20, history_window_turns=12)

    resp = client.patch("/api/settings", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["max_agent_steps"] == 20
    assert data["history_window_turns"] == 12


def test_patch_settings_creates_new_db_row(app: object, client: TestClient, testing_session_local) -> None:
    app.state.config_cache = _FakeConfigCache(_make_config())
    payload = _valid_patch_payload(max_agent_steps=15, agent_max_tool_calls=25)

    client.patch("/api/settings", json=payload)

    with testing_session_local() as db:
        row = RuntimeConfigRepo(db=db).get_active()
    assert row is not None
    assert row.config_json["limits"]["max_agent_steps"] == 15
    assert row.config_json["env_overrides"]["agent_max_tool_calls"] == 25


def test_patch_settings_persists_env_overrides_block(app: object, client: TestClient, testing_session_local) -> None:
    app.state.config_cache = _FakeConfigCache(_make_config())
    payload = _valid_patch_payload(
        eval_sample_rate=0.5,
        eval_llm_judge_enabled=False,
        prompt_injection_llm_check=True,
        agent_max_llm_calls=7,
        agent_max_execution_time_ms=15_000,
    )

    client.patch("/api/settings", json=payload)

    with testing_session_local() as db:
        row = RuntimeConfigRepo(db=db).get_active()
    env = row.config_json["env_overrides"]
    assert env["eval_sample_rate"] == pytest.approx(0.5)
    assert env["eval_llm_judge_enabled"] is False
    assert env["prompt_injection_llm_check"] is True
    assert env["agent_max_llm_calls"] == 7
    assert env["agent_max_execution_time_ms"] == 15_000


def test_patch_settings_updates_cache(app: object, client: TestClient) -> None:
    cache = _FakeConfigCache(_make_config())
    app.state.config_cache = cache
    payload = _valid_patch_payload(max_agent_steps=99, agent_max_tool_calls=5)

    client.patch("/api/settings", json=payload)

    updated = cache.get()
    assert updated.max_agent_steps == 99
    assert updated.agent_max_tool_calls == 5


def test_patch_settings_cache_has_new_id(app: object, client: TestClient) -> None:
    original_id = "aabbccdd-0000-0000-0000-000000000001"
    cache = _FakeConfigCache(_make_config(id=original_id))
    app.state.config_cache = cache

    client.patch("/api/settings", json=_valid_patch_payload())

    assert cache.get().id != original_id


# ── PATCH /api/settings — validation (422) ────────────────────────────────

@pytest.mark.parametrize(
    "override,field_hint",
    [
        ({"max_agent_steps": 0}, "max_agent_steps"),
        ({"max_agent_steps": -1}, "max_agent_steps"),
        ({"max_budget_usd": -0.01}, "max_budget_usd"),
        ({"eval_sample_rate": 1.1}, "eval_sample_rate"),
        ({"eval_sample_rate": -0.1}, "eval_sample_rate"),
        ({"agent_max_tool_calls": 0}, "agent_max_tool_calls"),
        ({"agent_max_llm_calls": 0}, "agent_max_llm_calls"),
        ({"agent_max_execution_time_ms": 0}, "agent_max_execution_time_ms"),
        ({"history_window_turns": 0}, "history_window_turns"),
    ],
)
def test_patch_settings_rejects_invalid_numeric_fields(
    app: object, client: TestClient, override: dict, field_hint: str
) -> None:
    app.state.config_cache = _FakeConfigCache(_make_config())

    resp = client.patch("/api/settings", json=_valid_patch_payload(**override))

    assert resp.status_code == 422, f"expected 422 for {field_hint}={override}"


def test_patch_settings_rejects_empty_model_id(app: object, client: TestClient) -> None:
    app.state.config_cache = _FakeConfigCache(_make_config())
    nodes = _all_nodes()
    nodes["planner"]["model_id"] = ""

    resp = client.patch("/api/settings", json=_valid_patch_payload(nodes=nodes))

    assert resp.status_code == 422


def test_patch_settings_rejects_empty_prompt_version(app: object, client: TestClient) -> None:
    app.state.config_cache = _FakeConfigCache(_make_config())
    nodes = _all_nodes()
    nodes["answer"]["prompt_version"] = ""

    resp = client.patch("/api/settings", json=_valid_patch_payload(nodes=nodes))

    assert resp.status_code == 422


def test_patch_settings_rejects_empty_judge_model_id(app: object, client: TestClient) -> None:
    app.state.config_cache = _FakeConfigCache(_make_config())

    resp = client.patch("/api/settings", json=_valid_patch_payload(eval_judge_model_id=""))

    assert resp.status_code == 422


def test_patch_settings_rejects_empty_bedrock_embedding_model_id(app: object, client: TestClient) -> None:
    app.state.config_cache = _FakeConfigCache(_make_config())

    resp = client.patch("/api/settings", json=_valid_patch_payload(bedrock_embedding_model_id=""))

    assert resp.status_code == 422


# ── RuntimeConfigData.from_db — env_overrides persistence ─────────────────

def test_from_db_reads_env_overrides_fields() -> None:
    row = _make_db_row({
        "nodes": {},
        "limits": {},
        "env_overrides": {
            "eval_sample_rate": 0.5,
            "eval_llm_judge_enabled": False,
            "eval_ragas_enabled": False,
            "eval_judge_model_id": "custom-judge-model",
            "prompt_injection_llm_check": True,
            "agent_max_tool_calls": 25,
            "agent_max_llm_calls": 8,
            "agent_max_execution_time_ms": 45_000,
            "bedrock_embedding_model_id": "custom-embedding-model",
        },
    })

    config = RuntimeConfigData.from_db(row)

    assert config.eval_sample_rate == pytest.approx(0.5)
    assert config.eval_llm_judge_enabled is False
    assert config.eval_ragas_enabled is False
    assert config.eval_judge_model_id == "custom-judge-model"
    assert config.prompt_injection_llm_check is True
    assert config.agent_max_tool_calls == 25
    assert config.agent_max_llm_calls == 8
    assert config.agent_max_execution_time_ms == 45_000
    assert config.bedrock_embedding_model_id == "custom-embedding-model"


def test_from_db_uses_dataclass_defaults_when_no_overrides() -> None:
    row = _make_db_row({"nodes": {}, "limits": {}})
    config = RuntimeConfigData.from_db(row)

    assert config.eval_sample_rate == pytest.approx(0.1)
    assert config.agent_max_tool_calls == 10
    assert config.prompt_injection_llm_check is False
    assert config.eval_llm_judge_enabled is True


def test_from_db_partial_env_overrides_use_defaults_for_missing_keys() -> None:
    row = _make_db_row({
        "nodes": {},
        "limits": {},
        "env_overrides": {"eval_sample_rate": 0.5, "agent_max_tool_calls": 3},
    })
    config = RuntimeConfigData.from_db(row)

    assert config.eval_sample_rate == pytest.approx(0.5)
    assert config.agent_max_tool_calls == 3
    assert config.eval_llm_judge_enabled is True
    assert config.prompt_injection_llm_check is False


def test_from_db_limits_block_parsed_correctly() -> None:
    row = _make_db_row({
        "nodes": {},
        "limits": {
            "max_agent_steps": 20,
            "max_budget_usd": 5.0,
            "history_window_turns": 8,
            "summarizer_prompt_version": "v2",
        },
    })

    config = RuntimeConfigData.from_db(row)

    assert config.max_agent_steps == 20
    assert config.max_budget_usd == pytest.approx(5.0)
    assert config.history_window_turns == 8
    assert config.summarizer_prompt_version == "v2"
