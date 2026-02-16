from __future__ import annotations

import json
import logging
from contextvars import ContextVar, Token
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import time

from opentelemetry import trace

_session_id_ctx: ContextVar[str] = ContextVar("opscopilot_session_id", default="")
_run_id_ctx: ContextVar[str] = ContextVar("opscopilot_run_id", default="")


def set_log_context(
    session_id: str | None = None,
    agent_run_id: str | None = None,
) -> tuple[Token[str], Token[str]]:
    session_value = _session_id_ctx.get() if session_id is None else session_id
    run_value = _run_id_ctx.get() if agent_run_id is None else agent_run_id
    session_token = _session_id_ctx.set(session_value)
    run_token = _run_id_ctx.set(run_value)
    return session_token, run_token


def reset_log_context(tokens: tuple[Token[str], Token[str]]) -> None:
    session_token, run_token = tokens
    _session_id_ctx.reset(session_token)
    _run_id_ctx.reset(run_token)


def clear_log_context() -> None:
    _session_id_ctx.set("")
    _run_id_ctx.set("")


class JsonLogFormatter(logging.Formatter):
    def __init__(self, service_name: str, datefmt: str | None = None):
        super().__init__(datefmt=datefmt)
        self._service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        span_context = trace.get_current_span().get_span_context()
        trace_id = ""
        span_id = ""
        if span_context.is_valid:
            trace_id = format(span_context.trace_id, "032x")
            span_id = format(span_context.span_id, "016x")

        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "component": record.name,
            "service": self._service_name,
            "message": record.getMessage(),
            "session_id": getattr(record, "session_id", _session_id_ctx.get()),
            "agent_run_id": getattr(record, "agent_run_id", _run_id_ctx.get()),
            "trace_id": trace_id,
            "span_id": span_id,
            "thread_id": record.thread,
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload.update(fields)
        return json.dumps(payload, default=str)


def configure_json_logging(
    *,
    service_name: str,
    level: str,
    root_config_attr: str,
    log_file: str | None = None,
    require_log_file: bool = False,
    backup_count: int = 14,
) -> None:
    root = logging.getLogger()
    if getattr(root, root_config_attr, False):
        return

    if require_log_file and not log_file:
        raise RuntimeError("log file path is required")

    formatter = JsonLogFormatter(service_name=service_name, datefmt="%Y-%m-%dT%H:%M:%S%z")
    formatter.converter = time.localtime

    handlers: list[logging.Handler] = []
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = TimedRotatingFileHandler(
            filename=str(log_path),
            when="midnight",
            interval=1,
            backupCount=backup_count,
            encoding="utf-8",
            utc=False,
        )
        file_handler.suffix = "%Y-%m-%d"
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    handlers.append(stream_handler)

    root.handlers.clear()
    for handler in handlers:
        root.addHandler(handler)
    root.setLevel(level.upper())
    setattr(root, root_config_attr, True)
