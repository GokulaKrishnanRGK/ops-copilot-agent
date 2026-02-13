from fastapi.testclient import TestClient

from opscopilot_api.routers.sessions_router import get_chat_service
from opscopilot_api.services.chat_service import SessionNotFoundError


class _FakeStreamService:
    def run_stream(self, session_id: str, prompt: str):
        if session_id == "missing":
            raise SessionNotFoundError("session not found")
        yield {
            "type": "agent_run.started",
            "timestamp": "2026-01-01T00:00:00+00:00",
            "session_id": session_id,
            "agent_run_id": "run-1",
            "payload": {"agent_run_id": "run-1"},
        }
        yield {
            "type": "assistant.token.delta",
            "timestamp": "2026-01-01T00:00:01+00:00",
            "session_id": session_id,
            "agent_run_id": "run-1",
            "payload": {"text": "hello"},
        }
        yield {
            "type": "agent_run.completed",
            "timestamp": "2026-01-01T00:00:02+00:00",
            "session_id": session_id,
            "agent_run_id": "run-1",
            "payload": {"summary": "completed"},
        }


class _CrashStreamService:
    def run_stream(self, session_id: str, prompt: str):
        yield {
            "type": "agent_run.started",
            "timestamp": "2026-01-01T00:00:00+00:00",
            "session_id": session_id,
            "agent_run_id": "run-1",
            "payload": {"agent_run_id": "run-1"},
        }
        raise RuntimeError("stream crashed")


class _ClarifyStreamService:
    def run_stream(self, session_id: str, prompt: str):  # noqa: ARG002
        yield {
            "type": "agent_run.started",
            "timestamp": "2026-01-01T00:00:00+00:00",
            "session_id": session_id,
            "agent_run_id": "run-1",
            "payload": {"agent_run_id": "run-1"},
        }
        yield {
            "type": "assistant.token.delta",
            "timestamp": "2026-01-01T00:00:01+00:00",
            "session_id": session_id,
            "agent_run_id": "run-1",
            "payload": {"text": "Which container should I use?"},
        }
        yield {
            "type": "agent_run.completed",
            "timestamp": "2026-01-01T00:00:02+00:00",
            "session_id": session_id,
            "agent_run_id": "run-1",
            "payload": {"summary": "clarification_required"},
        }


def test_chat_stream_endpoint_sends_sse_events(client: TestClient, app) -> None:
    app.dependency_overrides[get_chat_service] = lambda: _FakeStreamService()
    try:
        with client.stream(
            "POST",
            "/api/sessions/s1/chat/stream",
            json={"message": "status"},
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            chunks = list(response.iter_text())
        body = "".join(chunks)
        assert "event: agent_run.started" in body
        assert "event: assistant.token.delta" in body
        assert "event: agent_run.completed" in body
    finally:
        app.dependency_overrides.pop(get_chat_service, None)


def test_chat_stream_endpoint_not_found(client: TestClient, app) -> None:
    app.dependency_overrides[get_chat_service] = lambda: _FakeStreamService()
    try:
        with client.stream(
            "POST",
            "/api/sessions/missing/chat/stream",
            json={"message": "status"},
        ) as response:
            assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(get_chat_service, None)


def test_chat_stream_endpoint_stream_error_event(client: TestClient, app) -> None:
    app.dependency_overrides[get_chat_service] = lambda: _CrashStreamService()
    try:
        with client.stream(
            "POST",
            "/api/sessions/s1/chat/stream",
            json={"message": "status"},
        ) as response:
            assert response.status_code == 200
            body = "".join(list(response.iter_text()))
            assert "event: error" in body
            assert "runtime_error" in body
            assert "event: agent_run.failed" in body
    finally:
        app.dependency_overrides.pop(get_chat_service, None)


def test_chat_stream_endpoint_clarification_is_not_error_event(client: TestClient, app) -> None:
    app.dependency_overrides[get_chat_service] = lambda: _ClarifyStreamService()
    try:
        with client.stream(
            "POST",
            "/api/sessions/s1/chat/stream",
            json={"message": "status"},
        ) as response:
            assert response.status_code == 200
            body = "".join(list(response.iter_text()))
            assert "event: assistant.token.delta" in body
            assert "Which container should I use?" in body
            assert "event: agent_run.completed" in body
            assert "clarification_required" in body
            assert "event: error" not in body
            assert "event: agent_run.failed" not in body
    finally:
        app.dependency_overrides.pop(get_chat_service, None)
