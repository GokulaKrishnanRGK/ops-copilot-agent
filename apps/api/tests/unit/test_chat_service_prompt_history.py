from datetime import datetime, timedelta, timezone
from uuid import uuid4

from opscopilot_api.services.chat_service import ChatService
from opscopilot_db import models
from opscopilot_db.repositories import MessageRepo, SessionRepo


class _NoopRuntimeFactory:
    def create(self, recorder):  # noqa: ARG002
        raise RuntimeError("not used in this test")


def _create_session(session_repo: SessionRepo) -> str:
    session_id = str(uuid4())
    now = datetime.now(timezone.utc)
    session_repo.create(
        models.Session(
            id=session_id,
            title="history-test",
            created_at=now,
            updated_at=now,
        )
    )
    return session_id


def _add_message(
    message_repo: MessageRepo,
    *,
    session_id: str,
    role: str,
    content: str,
    created_at: datetime,
    metadata_json: dict | None = None,
) -> None:
    message_repo.create(
        models.Message(
            id=str(uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            created_at=created_at,
            metadata_json=metadata_json,
        )
    )


def test_prompt_history_preserves_completed_qa_pairs(testing_session_local) -> None:
    db = testing_session_local()
    try:
        session_repo = SessionRepo(db=db)
        message_repo = MessageRepo(db=db)
        session_id = _create_session(session_repo)
        t0 = datetime.now(timezone.utc)
        _add_message(message_repo, session_id=session_id, role="user", content="q1", created_at=t0)
        _add_message(
            message_repo,
            session_id=session_id,
            role="assistant",
            content="a1",
            created_at=t0 + timedelta(seconds=1),
        )
        _add_message(
            message_repo,
            session_id=session_id,
            role="user",
            content="q2",
            created_at=t0 + timedelta(seconds=2),
        )
        _add_message(
            message_repo,
            session_id=session_id,
            role="assistant",
            content="a2",
            created_at=t0 + timedelta(seconds=3),
        )

        service = ChatService(session_repo, message_repo, _NoopRuntimeFactory())
        history = service._load_prompt_history(session_id)
        assert history == ["User: q1\nAssistant: a1", "User: q2\nAssistant: a2"]
    finally:
        db.close()


def test_prompt_history_contains_active_clarification_chain(testing_session_local) -> None:
    db = testing_session_local()
    try:
        session_repo = SessionRepo(db=db)
        message_repo = MessageRepo(db=db)
        session_id = _create_session(session_repo)
        t0 = datetime.now(timezone.utc)
        _add_message(message_repo, session_id=session_id, role="user", content="q1", created_at=t0)
        _add_message(
            message_repo,
            session_id=session_id,
            role="assistant",
            content="need more info",
            created_at=t0 + timedelta(seconds=1),
            metadata_json={"clarification_required": True},
        )

        service = ChatService(session_repo, message_repo, _NoopRuntimeFactory())
        assert service._load_prompt_history(session_id) == ["q1"]
    finally:
        db.close()


def test_prompt_history_keeps_multiple_clarification_turns(testing_session_local) -> None:
    db = testing_session_local()
    try:
        session_repo = SessionRepo(db=db)
        message_repo = MessageRepo(db=db)
        session_id = _create_session(session_repo)
        t0 = datetime.now(timezone.utc)
        _add_message(message_repo, session_id=session_id, role="user", content="q1", created_at=t0)
        _add_message(
            message_repo,
            session_id=session_id,
            role="assistant",
            content="clarify 1",
            created_at=t0 + timedelta(seconds=1),
            metadata_json={"clarification_required": True},
        )
        _add_message(
            message_repo,
            session_id=session_id,
            role="user",
            content="q2",
            created_at=t0 + timedelta(seconds=2),
        )
        _add_message(
            message_repo,
            session_id=session_id,
            role="assistant",
            content="clarify 2",
            created_at=t0 + timedelta(seconds=3),
            metadata_json={"clarification_required": True},
        )

        service = ChatService(session_repo, message_repo, _NoopRuntimeFactory())
        assert service._load_prompt_history(session_id) == ["q1", "q2"]
    finally:
        db.close()


def test_prompt_history_clears_clarification_chain_after_answer(testing_session_local) -> None:
    db = testing_session_local()
    try:
        session_repo = SessionRepo(db=db)
        message_repo = MessageRepo(db=db)
        session_id = _create_session(session_repo)
        t0 = datetime.now(timezone.utc)
        _add_message(message_repo, session_id=session_id, role="user", content="q1", created_at=t0)
        _add_message(
            message_repo,
            session_id=session_id,
            role="assistant",
            content="clarify 1",
            created_at=t0 + timedelta(seconds=1),
            metadata_json={"clarification_required": True},
        )
        _add_message(
            message_repo,
            session_id=session_id,
            role="user",
            content="clarification response",
            created_at=t0 + timedelta(seconds=2),
        )
        _add_message(
            message_repo,
            session_id=session_id,
            role="assistant",
            content="final answer",
            created_at=t0 + timedelta(seconds=3),
        )

        service = ChatService(session_repo, message_repo, _NoopRuntimeFactory())
        history = service._load_prompt_history(session_id)
        assert history == ["User: clarification response\nAssistant: final answer"]
        assert not any("q1" in h for h in history)
    finally:
        db.close()


def test_prompt_history_completed_turns_plus_active_clarification(testing_session_local) -> None:
    """Completed Q&A pairs are preserved and combined with the active clarification chain."""
    db = testing_session_local()
    try:
        session_repo = SessionRepo(db=db)
        message_repo = MessageRepo(db=db)
        session_id = _create_session(session_repo)
        t0 = datetime.now(timezone.utc)
        _add_message(message_repo, session_id=session_id, role="user", content="list pods in opscopilot-demo", created_at=t0)
        _add_message(
            message_repo,
            session_id=session_id,
            role="assistant",
            content="There are 2 pods: pod-a, pod-b",
            created_at=t0 + timedelta(seconds=1),
        )
        _add_message(
            message_repo,
            session_id=session_id,
            role="user",
            content="get logs from pod-a",
            created_at=t0 + timedelta(seconds=2),
        )
        _add_message(
            message_repo,
            session_id=session_id,
            role="assistant",
            content="Which namespace?",
            created_at=t0 + timedelta(seconds=3),
            metadata_json={"clarification_required": True},
        )

        service = ChatService(session_repo, message_repo, _NoopRuntimeFactory())
        history = service._load_prompt_history(session_id)
        assert history == [
            "User: list pods in opscopilot-demo\nAssistant: There are 2 pods: pod-a, pod-b",
            "get logs from pod-a",
        ]
    finally:
        db.close()


def test_prompt_history_empty_for_new_session(testing_session_local) -> None:
    db = testing_session_local()
    try:
        session_repo = SessionRepo(db=db)
        message_repo = MessageRepo(db=db)
        session_id = _create_session(session_repo)

        service = ChatService(session_repo, message_repo, _NoopRuntimeFactory())
        assert service._load_prompt_history(session_id) == []
    finally:
        db.close()
