from dataclasses import dataclass

from fastapi.testclient import TestClient

from opscopilot_api.routers.sessions_router import get_chat_service
from opscopilot_api.services.chat_service import ChatService
from opscopilot_api.services.runtime_factory import RuntimeFactory
from opscopilot_db.repositories import MessageRepo, SessionRepo


@dataclass(frozen=True)
class _FakeResult:
    answer: str | None
    error: dict | None


class _FakeRuntime:
    def run(self, _state):
        return _FakeResult(answer="ok", error=None)


class _FakeRuntimeFactory(RuntimeFactory):
    def create(self, recorder):  # noqa: ARG002
        return _FakeRuntime()


def test_messages_and_runs_list_by_session(client: TestClient, app, testing_session_local) -> None:
    def _override_chat_service():
        db = testing_session_local()
        try:
            yield ChatService(
                session_repo=SessionRepo(db=db),
                message_repo=MessageRepo(db=db),
                runtime_factory=_FakeRuntimeFactory(),
            )
        finally:
            db.close()

    app.dependency_overrides[get_chat_service] = _override_chat_service
    try:
        create_resp = client.post("/api/sessions", json={"title": "list-check"})
        assert create_resp.status_code == 201
        session_id = create_resp.json()["id"]

        chat_resp = client.post(
            f"/api/sessions/{session_id}/chat",
            json={"message": "status"},
        )
        assert chat_resp.status_code == 200

        messages_resp = client.get("/api/messages", params={"session_id": session_id})
        assert messages_resp.status_code == 200
        assert len(messages_resp.json()["items"]) >= 2

        runs_resp = client.get("/api/runs", params={"session_id": session_id})
        assert runs_resp.status_code == 200
        assert len(runs_resp.json()["items"]) >= 1
    finally:
        app.dependency_overrides.pop(get_chat_service, None)
