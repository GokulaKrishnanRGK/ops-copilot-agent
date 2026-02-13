from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from opscopilot_agent_runtime.persistence import AgentRunRecorder
from opscopilot_agent_runtime.state import AgentState
from opscopilot_db import models, repositories

from .event_mapper import (
    agent_run_completed,
    agent_run_failed,
    agent_run_started,
    assistant_delta,
    error_event,
)
from .runtime_factory import RuntimeFactory


@dataclass(frozen=True)
class ChatResult:
    run_id: str
    answer: str | None
    error: dict | None


class SessionNotFoundError(ValueError):
    pass


class ChatExecutionError(RuntimeError):
    pass


class ChatService:
    def __init__(
        self,
        session_repo: repositories.SessionRepository,
        message_repo: repositories.MessageRepository,
        runtime_factory: RuntimeFactory,
    ) -> None:
        self._session_repo = session_repo
        self._message_repo = message_repo
        self._runtime_factory = runtime_factory

    def run(self, session_id: str, prompt: str) -> ChatResult:
        session = self._session_repo.get(session_id)
        if session is None:
            raise SessionNotFoundError("session not found")

        now = datetime.now(timezone.utc)
        self._message_repo.create(
            models.Message(
                id=str(uuid4()),
                session_id=session_id,
                role="user",
                content=prompt,
                created_at=now,
                metadata_json=None,
            )
        )

        run_id = str(uuid4())
        recorder = AgentRunRecorder(session_id=session_id, run_id=run_id)
        runtime = self._runtime_factory.create(recorder=recorder)
        try:
            result = runtime.run(AgentState(prompt=prompt))
        except Exception as exc:
            raise ChatExecutionError("agent runtime failed") from exc

        answer_text = result.answer
        if answer_text is None and result.error:
            answer_text = result.error.get("message", "request failed")
        self._message_repo.create(
            models.Message(
                id=str(uuid4()),
                session_id=session_id,
                role="assistant",
                content=answer_text or "",
                created_at=datetime.now(timezone.utc),
                metadata_json={"error": result.error} if result.error else None,
            )
        )

        return ChatResult(run_id=run_id, answer=result.answer, error=result.error)

    def run_stream(self, session_id: str, prompt: str):
        session = self._session_repo.get(session_id)
        if session is None:
            raise SessionNotFoundError("session not found")

        run_id = str(uuid4())
        now = datetime.now(timezone.utc)
        self._message_repo.create(
            models.Message(
                id=str(uuid4()),
                session_id=session_id,
                role="user",
                content=prompt,
                created_at=now,
                metadata_json=None,
            )
        )

        def _stream():
            yield agent_run_started(session_id, run_id)

            recorder = AgentRunRecorder(session_id=session_id, run_id=run_id)
            runtime = self._runtime_factory.create(recorder=recorder)
            try:
                result = runtime.run(AgentState(prompt=prompt))
            except Exception as exc:
                message = str(exc) or "agent runtime failed"
                self._message_repo.create(
                    models.Message(
                        id=str(uuid4()),
                        session_id=session_id,
                        role="assistant",
                        content=message,
                        created_at=datetime.now(timezone.utc),
                        metadata_json={"error": {"type": "runtime_error", "message": message}},
                    )
                )
                yield error_event(session_id, run_id, "runtime_error", message)
                yield agent_run_failed(session_id, run_id, message, "runtime_error")
                return

            if result.error:
                error_message = result.error.get("message", "request failed")
                self._message_repo.create(
                    models.Message(
                        id=str(uuid4()),
                        session_id=session_id,
                        role="assistant",
                        content=error_message,
                        created_at=datetime.now(timezone.utc),
                        metadata_json={"error": result.error},
                    )
                )
                failure_type = result.error.get("type", "runtime_error")
                yield error_event(session_id, run_id, failure_type, error_message, result.error)
                yield agent_run_failed(session_id, run_id, error_message, failure_type)
                return

            answer_text = result.answer or ""
            self._message_repo.create(
                models.Message(
                    id=str(uuid4()),
                    session_id=session_id,
                    role="assistant",
                    content=answer_text,
                    created_at=datetime.now(timezone.utc),
                    metadata_json=None,
                )
            )
            yield assistant_delta(session_id, run_id, answer_text)
            yield agent_run_completed(session_id, run_id)

        return _stream()
