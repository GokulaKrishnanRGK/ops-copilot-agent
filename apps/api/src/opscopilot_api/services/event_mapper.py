from datetime import datetime, timezone


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_event(
    *,
    event_type: str,
    session_id: str,
    run_id: str,
    payload: dict,
) -> dict:
    return {
        "type": event_type,
        "timestamp": _ts(),
        "session_id": session_id,
        "agent_run_id": run_id,
        "payload": payload,
    }


def agent_run_started(session_id: str, run_id: str) -> dict:
    return make_event(
        event_type="agent_run.started",
        session_id=session_id,
        run_id=run_id,
        payload={"agent_run_id": run_id},
    )


def agent_run_completed(session_id: str, run_id: str, summary: str = "completed") -> dict:
    return make_event(
        event_type="agent_run.completed",
        session_id=session_id,
        run_id=run_id,
        payload={"summary": summary},
    )


def assistant_delta(session_id: str, run_id: str, text: str) -> dict:
    return make_event(
        event_type="assistant.token.delta",
        session_id=session_id,
        run_id=run_id,
        payload={"text": text},
    )


def error_event(session_id: str, run_id: str, error_type: str, message: str, context: dict | None = None) -> dict:
    return make_event(
        event_type="error",
        session_id=session_id,
        run_id=run_id,
        payload={
            "error_type": error_type,
            "message": message,
            "context": context or {},
        },
    )


def agent_run_failed(session_id: str, run_id: str, reason: str, failure_type: str) -> dict:
    return make_event(
        event_type="agent_run.failed",
        session_id=session_id,
        run_id=run_id,
        payload={"reason": reason, "failure_type": failure_type},
    )
