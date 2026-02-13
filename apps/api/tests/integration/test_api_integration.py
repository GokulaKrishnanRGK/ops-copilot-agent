from dataclasses import dataclass
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from opscopilot_api.routers.sessions_router import get_chat_service
from opscopilot_api.services.chat_service import ChatService
from opscopilot_api.services.runtime_factory import RuntimeFactory
from opscopilot_agent_runtime.state import AgentState
from opscopilot_agent_runtime.runtime.events import AgentEvent
from opscopilot_db import models
from opscopilot_db.connection import get_sessionmaker
from opscopilot_db.repositories import MessageRepo, SessionRepo


@dataclass(frozen=True)
class _FakeResult:
    answer: str | None
    error: dict | None


class _FakeRuntime:
    def run(self, _state):
        return _FakeResult(answer="integration-answer", error=None)

    def run_stream(self, state):  # noqa: ARG002
        yield AgentState(event=AgentEvent(event_type="planner.completed", payload={"steps": 1}))
        yield AgentState(answer="integration-answer")


class _FakeRuntimeFactory(RuntimeFactory):
    def create(self, recorder):  # noqa: ARG002
        return _FakeRuntime()


class _NoopRecorder:
    pass


def _recorder_factory(session_id: str, run_id: str):  # noqa: ARG001
    return _NoopRecorder()


def _override_chat_service():
    sessionmaker = get_sessionmaker()
    db = sessionmaker()
    try:
        yield ChatService(
            session_repo=SessionRepo(db=db),
            message_repo=MessageRepo(db=db),
            runtime_factory=_FakeRuntimeFactory(),
            recorder_factory=_recorder_factory,
        )
    finally:
        db.close()


@pytest.mark.integration
def test_session_crud_integration(client: TestClient) -> None:
    create_resp = client.post("/api/sessions", json={"title": "integration"})
    assert create_resp.status_code == 201
    session_id = create_resp.json()["id"]

    list_resp = client.get("/api/sessions")
    assert list_resp.status_code == 200
    assert any(item["id"] == session_id for item in list_resp.json()["items"])

    patch_resp = client.patch(f"/api/sessions/{session_id}", json={"title": "updated"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == "updated"

    delete_resp = client.delete(f"/api/sessions/{session_id}")
    assert delete_resp.status_code == 204


@pytest.mark.integration
def test_chat_and_stream_integration(client: TestClient, app) -> None:
    app.dependency_overrides[get_chat_service] = _override_chat_service
    try:
        create_resp = client.post("/api/sessions", json={"title": f"s-{uuid4()}"})
        assert create_resp.status_code == 201
        session_id = create_resp.json()["id"]

        with client.stream(
            "POST",
            f"/api/sessions/{session_id}/chat/stream",
            json={"message": "status stream"},
        ) as response:
            assert response.status_code == 200
            body = "".join(list(response.iter_text()))
        assert "event: agent_run.started" in body
        assert "event: assistant.token.delta" in body
        assert "integration-answer" in body

        sessionmaker = get_sessionmaker()
        with sessionmaker() as db:
            messages = db.query(models.Message).filter(models.Message.session_id == session_id).all()
            assert len(messages) >= 2
    finally:
        app.dependency_overrides.pop(get_chat_service, None)
