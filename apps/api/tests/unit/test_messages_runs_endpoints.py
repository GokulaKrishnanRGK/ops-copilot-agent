from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from opscopilot_api.routers.sessions_router import get_chat_service
from opscopilot_api.services.chat_service import ChatService
from opscopilot_db import models
from opscopilot_db.repositories import MessageRepo, SessionRepo


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class _FakeResult:
    answer: str | None
    error: dict | None


class _FakeRuntime:
    def run(self, _state):
        return _FakeResult(answer="ok", error=None)


class _FakeRuntimeFactory:
    def create(self, recorder):  # noqa: ARG002
        return _FakeRuntime()


class _NoopRecorder:
    pass


def _recorder_factory(session_id: str, run_id: str):  # noqa: ARG001
    return _NoopRecorder()


def test_messages_and_runs_list_by_session(client: TestClient, app, testing_session_local) -> None:
    def _override_chat_service():
        db = testing_session_local()
        try:
            yield ChatService(
                session_repo=SessionRepo(db=db),
                message_repo=MessageRepo(db=db),
                runtime_factory=_FakeRuntimeFactory(),
                recorder_factory=_recorder_factory,
            )
        finally:
            db.close()

    app.dependency_overrides[get_chat_service] = _override_chat_service
    try:
        create_resp = client.post("/api/sessions", json={"title": "list-check"})
        assert create_resp.status_code == 201
        session_id = create_resp.json()["id"]

        with client.stream(
            "POST",
            f"/api/sessions/{session_id}/chat/stream",
            json={"message": "status"},
        ) as response:
            assert response.status_code == 200
            body = "".join(list(response.iter_text()))
        assert "event: agent_run.started" in body

        messages_resp = client.get("/api/messages", params={"session_id": session_id})
        assert messages_resp.status_code == 200
        assert len(messages_resp.json()["items"]) >= 2

        runs_resp = client.get("/api/runs", params={"session_id": session_id})
        assert runs_resp.status_code == 200
        payload = runs_resp.json()
        assert isinstance(payload["items"], list)
        assert "session_metrics" in payload
        assert payload["session_metrics"]["run_count"] >= 1
    finally:
        app.dependency_overrides.pop(get_chat_service, None)


def test_runs_include_gateway_and_budget_visibility(client: TestClient, testing_session_local) -> None:
    db = testing_session_local()
    try:
        session = models.Session(
            id="s-metrics",
            created_at=_now(),
            updated_at=_now(),
            title=None,
        )
        run = models.AgentRun(
            id="r-metrics",
            session_id=session.id,
            started_at=_now(),
            ended_at=None,
            status="completed",
            config_json={"budget": {"max_usd": 1.0}},
        )
        db.add(session)
        db.add(run)
        db.add(
            models.LlmCall(
                id="c1",
                agent_run_id=run.id,
                agent_node="planner",
                model_id="anthropic.claude-3-sonnet",
                tokens_input=10,
                tokens_output=5,
                cost_usd=0.25,
                latency_ms=100,
                created_at=_now(),
                metadata_json={"provider": "bedrock"},
            )
        )
        db.add(
            models.BudgetEvent(
                id="b1",
                agent_run_id=run.id,
                kind="llm_call",
                delta_usd=0.25,
                total_usd=0.25,
                created_at=_now(),
                metadata_json=None,
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/api/runs", params={"session_id": "s-metrics"})

    assert response.status_code == 200
    payload = response.json()
    metrics = payload["items"][0]["metrics"]
    assert metrics["model_usage"] == [
        {
            "provider": "bedrock",
            "model_id": "anthropic.claude-3-sonnet",
            "tokens_input": 10,
            "tokens_output": 5,
            "tokens_total": 15,
            "cost_usd": 0.25,
            "llm_call_count": 1,
        }
    ]
    assert metrics["budget"]["max_usd"] == 1.0
    assert metrics["budget"]["remaining_usd"] == 0.75
    assert metrics["budget"]["status"] == "available"
    assert payload["session_metrics"]["budget"]["max_usd"] == 1.0
    assert payload["session_metrics"]["budget"]["remaining_usd"] == 0.75
    assert payload["session_metrics"]["budget"]["status"] == "available"
