from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

from opscopilot_db import models
from opscopilot_db.connection import get_sessionmaker


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _session_id() -> str:
    return os.getenv("AGENT_SESSION_ID", "session")


def _run_id() -> str:
    return os.getenv("AGENT_RUN_ID", str(uuid.uuid4()))


def _bytes_for(payload: object) -> int:
    try:
        return len(json.dumps(payload).encode("utf-8"))
    except Exception:
        return 0


def _structured_tool_response(response: dict) -> dict:
    structured = response.get("structured_content")
    if isinstance(structured, dict):
        return structured
    return {}


def _tool_result_payload(tool_name: str, structured_response: dict) -> dict | None:
    result = structured_response.get("result")
    if not isinstance(result, dict):
        return None
    if tool_name == "k8s.get_pod_logs":
        return result
    return None


class AgentRunRecorder:
    def __init__(self, session_id: str | None = None, run_id: str | None = None) -> None:
        self._session_id = session_id or _session_id()
        self._run_id = run_id or _run_id()
        self._sessionmaker = get_sessionmaker()

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def run_id(self) -> str:
        return self._run_id

    def start(self, config_json: dict) -> None:
        with self._sessionmaker() as db:
            session = db.get(models.Session, self._session_id)
            if session is None:
                now = _now()
                db.add(
                    models.Session(
                        id=self._session_id,
                        created_at=now,
                        updated_at=now,
                        title=None,
                    )
                )
                db.flush()
            db.add(
                models.AgentRun(
                    id=self._run_id,
                    session_id=self._session_id,
                    started_at=_now(),
                    ended_at=None,
                    status="running",
                    config_json=config_json,
                )
            )
            db.commit()

    def finish(self, status: str) -> None:
        with self._sessionmaker() as db:
            run = db.get(models.AgentRun, self._run_id)
            if run is None:
                return
            run.status = status
            run.ended_at = _now()
            db.commit()

    def record_llm_call(
        self,
        agent_node: str,
        model_id: str,
        tokens_input: int,
        tokens_output: int,
        cost_usd: float,
        latency_ms: int,
        metadata_json: dict | None = None,
    ) -> None:
        with self._sessionmaker() as db:
            db.add(
                models.LlmCall(
                    id=str(uuid.uuid4()),
                    agent_run_id=self._run_id,
                    agent_node=agent_node,
                    model_id=model_id,
                    tokens_input=tokens_input,
                    tokens_output=tokens_output,
                    cost_usd=cost_usd,
                    latency_ms=latency_ms,
                    created_at=_now(),
                    metadata_json=metadata_json,
                )
            )
            db.commit()

    def record_budget_event(self, kind: str, delta_usd: float, total_usd: float) -> None:
        with self._sessionmaker() as db:
            db.add(
                models.BudgetEvent(
                    id=str(uuid.uuid4()),
                    agent_run_id=self._run_id,
                    kind=kind,
                    delta_usd=delta_usd,
                    total_usd=total_usd,
                    created_at=_now(),
                    metadata_json=None,
                )
            )
            db.commit()

    def record_tool_call(self, tool_name: str, args: dict, response: dict) -> None:
        structured = _structured_tool_response(response)
        error_message = None
        status = structured.get("status")
        if status != "success":
            error = structured.get("error")
            if isinstance(error, dict):
                error_message_value = error.get("message")
                if isinstance(error_message_value, str):
                    error_message = error_message_value
        result_payload = _tool_result_payload(tool_name, structured)
        latency_ms_raw = structured.get("latency_ms", 0)
        if isinstance(latency_ms_raw, int):
            latency_ms = latency_ms_raw
        else:
            latency_ms = 0
        with self._sessionmaker() as db:
            db.add(
                models.ToolCall(
                    id=str(uuid.uuid4()),
                    agent_run_id=self._run_id,
                    tool_name=tool_name,
                    args_json=args,
                    status=status or "error",
                    latency_ms=latency_ms,
                    bytes_returned=_bytes_for(result_payload),
                    truncated=bool(structured.get("truncated")),
                    result_json=result_payload,
                    error_message=error_message,
                    created_at=_now(),
                )
            )
            db.commit()
