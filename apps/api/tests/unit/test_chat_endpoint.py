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
        return _FakeResult(answer="hello from runtime", error=None)


class _FakeRuntimeFactory(RuntimeFactory):
    def create(self, recorder):  # noqa: ARG002
        return _FakeRuntime()


class _FailRuntime:
    def run(self, _state):
        raise RuntimeError("boom")


class _FailRuntimeFactory(RuntimeFactory):
    def create(self, recorder):  # noqa: ARG002
        return _FailRuntime()


def test_chat_endpoint_runs_runtime(
    client: TestClient,
    app,
    testing_session_local,
) -> None:
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
        create_resp = client.post("/api/sessions", json={"title": "chat"})
        assert create_resp.status_code == 201
        session_id = create_resp.json()["id"]

        chat_resp = client.post(
            f"/api/sessions/{session_id}/chat",
            json={"message": "what is status"},
        )
        assert chat_resp.status_code == 200
        body = chat_resp.json()
        assert body["answer"] == "hello from runtime"
        assert body["error"] is None
        assert body["run_id"]
    finally:
        app.dependency_overrides.pop(get_chat_service, None)


def test_chat_endpoint_runtime_error_returns_500(
    client: TestClient,
    app,
    testing_session_local,
) -> None:
    def _override_chat_service():
        db = testing_session_local()
        try:
            yield ChatService(
                session_repo=SessionRepo(db=db),
                message_repo=MessageRepo(db=db),
                runtime_factory=_FailRuntimeFactory(),
            )
        finally:
            db.close()

    app.dependency_overrides[get_chat_service] = _override_chat_service
    try:
        create_resp = client.post("/api/sessions", json={"title": "chat"})
        assert create_resp.status_code == 201
        session_id = create_resp.json()["id"]
        chat_resp = client.post(
            f"/api/sessions/{session_id}/chat",
            json={"message": "what is status"},
        )
        assert chat_resp.status_code == 500
        assert chat_resp.json()["detail"] == "agent runtime failed"
    finally:
        app.dependency_overrides.pop(get_chat_service, None)
