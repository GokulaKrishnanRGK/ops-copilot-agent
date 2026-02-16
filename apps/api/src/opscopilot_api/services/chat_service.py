from dataclasses import dataclass
from datetime import datetime, timezone
from collections.abc import Iterable
from typing import Callable
from queue import Empty, Queue
import threading
import time
import logging
from uuid import uuid4
from opentelemetry import context as otel_context, metrics, trace

from opscopilot_agent_runtime.persistence import AgentRunRecorder
from opscopilot_agent_runtime.state import AgentState
from opscopilot_db import models, repositories

from .event_mapper import (
    agent_run_completed,
    agent_run_started,
    runtime_event,
)
from opscopilot_api.logging import clear_log_context, set_log_context
from .runtime_factory import RuntimeFactory
from .stream_decisions import (
    StreamEventDecider,
    StreamLifecycleTracker,
    terminal_item_from_state,
    terminal_stream_events,
)


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
        recorder_factory: Callable[[str, str], AgentRunRecorder] = AgentRunRecorder,
    ) -> None:
        self._session_repo = session_repo
        self._message_repo = message_repo
        self._runtime_factory = runtime_factory
        self._recorder_factory = recorder_factory
        self._tracer = trace.get_tracer("opscopilot_api.chat")
        self._logger = logging.getLogger("opscopilot_api.chat")
        meter = metrics.get_meter("opscopilot_api.chat")
        self._agent_runs_total = meter.create_counter("agent_runs_total")
        self._agent_run_failures_total = meter.create_counter("agent_run_failures_total")
        self._agent_run_duration_ms = meter.create_histogram("agent_run_duration_ms")

    def _load_prompt_history(self, session_id: str) -> list[str]:
        messages = list(self._message_repo.list_by_session(session_id))
        history: list[str] = []
        pending_user_prompt: str | None = None
        for message in messages:
            content = (message.content or "").strip()
            if not content:
                continue
            if message.role == "user":
                pending_user_prompt = content
                continue
            if message.role != "assistant":
                continue
            if not pending_user_prompt:
                continue
            metadata = message.metadata_json if isinstance(message.metadata_json, dict) else {}
            error = metadata.get("error")
            is_clarification = bool(metadata.get("clarification_required")) or (
                isinstance(error, dict) and error.get("type") == "clarification_required"
            )
            if is_clarification:
                history.append(pending_user_prompt)
            else:
                # A non-clarification assistant response closes any prior clarification chain.
                history = []
            pending_user_prompt = None
        return history

    @staticmethod
    def _is_clarification(result_error: dict | None) -> bool:
        return bool(result_error and result_error.get("type") == "clarification_required")

    @staticmethod
    def _chunk_text(text: str, max_len: int = 40) -> list[str]:
        words = text.split(" ")
        if not words:
            return [text]
        chunks: list[str] = []
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if len(candidate) <= max_len:
                current = candidate
            else:
                if current:
                    chunks.append(current + " ")
                current = word
        if current:
            chunks.append(current)
        return chunks

    @staticmethod
    def _tool_log_events(session_id: str, run_id: str, tool_results: list | None) -> list[dict]:
        if not tool_results:
            return []
        items: list[dict] = []
        for result in tool_results:
            tool_name = getattr(result, "tool_name", None)
            if not isinstance(tool_name, str) or tool_name != "k8s.get_pod_logs":
                continue
            tool_response = getattr(result, "result", None)
            if not isinstance(tool_response, dict):
                continue
            structured = tool_response.get("structured_content")
            if not isinstance(structured, dict):
                continue
            payload = structured.get("result")
            if not isinstance(payload, dict):
                continue
            text = payload.get("text")
            if not isinstance(text, str) or not text.strip():
                fallback = payload.get("logs")
                if isinstance(fallback, str) and fallback.strip():
                    text = fallback
                else:
                    continue
            step_id = getattr(result, "step_id", "")
            if not isinstance(step_id, str):
                step_id = ""
            items.append(
                {
                    "step_id": step_id,
                    "tool_name": tool_name,
                    "text": text,
                    "truncated": bool(structured.get("truncated")),
                }
            )
        if not items:
            return []
        return [runtime_event(session_id, run_id, "tool.logs.available", {"items": items})]

    @staticmethod
    def _runtime_states(runtime: object, initial_state: AgentState) -> Iterable[AgentState]:
        run_stream = getattr(runtime, "run_stream", None)
        if callable(run_stream):
            return run_stream(initial_state)
        run = getattr(runtime, "run", None)
        if callable(run):
            result = run(initial_state)
            if isinstance(result, AgentState):
                return [result]
            answer = getattr(result, "answer", None)
            error = getattr(result, "error", None)
            return [initial_state.merge(answer=answer, error=error)]
        raise AttributeError("runtime does not implement run_stream or run")

    def run(self, session_id: str, prompt: str) -> ChatResult:
        session = self._session_repo.get(session_id)
        if session is None:
            raise SessionNotFoundError("session not found")

        run_id = str(uuid4())
        started = time.perf_counter()
        set_log_context(session_id=session_id, agent_run_id=run_id)
        try:
            with self._tracer.start_as_current_span("chat.run") as span:
                span.set_attribute("session_id", session_id)
                span.set_attribute("agent_run_id", run_id)
                self._logger.info("chat run started")
                self._agent_runs_total.add(1, {"entrypoint": "run"})
                prompt_history = self._load_prompt_history(session_id)
                now = datetime.now(timezone.utc)
                self._message_repo.create(
                    models.Message(
                        id=str(uuid4()),
                        session_id=session_id,
                        role="user",
                        content=prompt,
                        created_at=now,
                        metadata_json={"run_id": run_id},
                    )
                )
                recorder = self._recorder_factory(session_id, run_id)
                runtime = self._runtime_factory.create(recorder=recorder)
                try:
                    result = runtime.run(AgentState(prompt=prompt, prompt_history=prompt_history))
                except Exception as exc:
                    span.record_exception(exc)
                    self._logger.exception("chat run runtime failed")
                    self._agent_run_failures_total.add(
                        1,
                        {"entrypoint": "run", "failure_type": "runtime_error"},
                    )
                    raise ChatExecutionError("agent runtime failed") from exc

                answer_text = result.answer
                if answer_text is None and result.error:
                    answer_text = result.error.get("message", "request failed")
                clarification = self._is_clarification(result.error)
                assistant_metadata: dict | None
                if clarification:
                    assistant_metadata = {"clarification_required": True}
                elif result.error:
                    assistant_metadata = {"error": result.error}
                else:
                    assistant_metadata = None
                if result.error and not clarification:
                    failure_type = result.error.get("type") if isinstance(result.error, dict) else "unknown"
                    failure_type_value = (
                        failure_type if isinstance(failure_type, str) and failure_type else "unknown"
                    )
                    self._agent_run_failures_total.add(
                        1,
                        {"entrypoint": "run", "failure_type": failure_type_value},
                    )
                if assistant_metadata is None:
                    assistant_metadata = {"run_id": run_id}
                else:
                    assistant_metadata = {**assistant_metadata, "run_id": run_id}
                self._message_repo.create(
                    models.Message(
                        id=str(uuid4()),
                        session_id=session_id,
                        role="assistant",
                        content=answer_text or "",
                        created_at=datetime.now(timezone.utc),
                        metadata_json=assistant_metadata,
                    )
                )

                return ChatResult(
                    run_id=run_id,
                    answer=answer_text,
                    error=None if clarification else result.error,
                )
        finally:
            self._logger.info("chat run finished")
            self._agent_run_duration_ms.record(
                (time.perf_counter() - started) * 1000.0,
                {"entrypoint": "run"},
            )
            clear_log_context()

    def run_stream(self, session_id: str, prompt: str):
        session = self._session_repo.get(session_id)
        if session is None:
            raise SessionNotFoundError("session not found")

        run_id = str(uuid4())
        prompt_history = self._load_prompt_history(session_id)
        now = datetime.now(timezone.utc)
        self._message_repo.create(
            models.Message(
                id=str(uuid4()),
                session_id=session_id,
                role="user",
                content=prompt,
                created_at=now,
                metadata_json={"run_id": run_id},
            )
        )

        def _stream():
            started = time.perf_counter()
            set_log_context(session_id=session_id, agent_run_id=run_id)
            try:
                with self._tracer.start_as_current_span("chat.run_stream") as span:
                    span.set_attribute("session_id", session_id)
                    span.set_attribute("agent_run_id", run_id)
                    self._logger.info("chat stream started")
                    self._agent_runs_total.add(1, {"entrypoint": "run_stream"})
                    yield agent_run_started(session_id, run_id)

                    recorder = self._recorder_factory(session_id, run_id)
                    runtime = self._runtime_factory.create(recorder=recorder)
                    decider = StreamEventDecider()
                    tracker = StreamLifecycleTracker()
                    queue: Queue = Queue()
                    done = object()
                    worker_parent_context = otel_context.get_current()

                    def on_llm_delta(node: str, text: str) -> None:
                        events = decider.llm_delta_events(
                            session_id=session_id,
                            run_id=run_id,
                            node=node,
                            text=text,
                            tracker=tracker,
                        )
                        for event in events:
                            queue.put(event)

                    def worker():
                        try:
                            answer_emitted = False
                            last_state = AgentState(prompt=prompt, prompt_history=prompt_history)
                            for state in self._runtime_states(
                                runtime,
                                AgentState(
                                    prompt=prompt,
                                    prompt_history=prompt_history,
                                    llm_stream_callback=on_llm_delta,
                                ),
                            ):
                                last_state = state
                                state_event = getattr(state, "event", None)
                                if state_event is not None:
                                    if state_event.event_type == "tool_executor.completed":
                                        for log_event in self._tool_log_events(
                                            session_id=session_id,
                                            run_id=run_id,
                                            tool_results=getattr(state, "tool_results", None),
                                        ):
                                            queue.put(log_event)
                                    events = decider.runtime_events(
                                        session_id=session_id,
                                        run_id=run_id,
                                        event_type=state_event.event_type,
                                        payload=state_event.payload or {},
                                        tracker=tracker,
                                        answer_message=getattr(state, "answer", None),
                                    )
                                    for event in events:
                                        queue.put(event)
                                terminal_item, answer_emitted = terminal_item_from_state(
                                    state=state,
                                    answer_emitted=answer_emitted,
                                    is_clarification=self._is_clarification,
                                )
                                if terminal_item is not None:
                                    queue.put(terminal_item)
                                    return

                            if last_state.answer:
                                queue.put({"__terminal__": "answer", "message": last_state.answer})
                                return
                            message = "agent runtime completed without an assistant response"
                            queue.put(
                                {
                                    "__terminal__": "error",
                                    "message": message,
                                    "failure_type": "runtime_error",
                                    "context": {"type": "runtime_error", "message": message},
                                }
                            )
                        except Exception as exc:
                            self._logger.exception("chat stream runtime failed")
                            message = str(exc) or "agent runtime failed"
                            queue.put(
                                {
                                    "__terminal__": "error",
                                    "message": message,
                                    "failure_type": "runtime_error",
                                    "context": {"type": "runtime_error", "message": message},
                                }
                            )
                            queue.put(done)

                    def worker_entrypoint():
                        token = otel_context.attach(worker_parent_context)
                        set_log_context(session_id=session_id, agent_run_id=run_id)
                        try:
                            worker()
                        finally:
                            clear_log_context()
                            otel_context.detach(token)

                    thread = threading.Thread(target=worker_entrypoint, daemon=True)
                    thread.start()
                    token_emitted = False
                    while True:
                        try:
                            item = queue.get(timeout=0.2)
                        except Empty:
                            if not thread.is_alive():
                                break
                            continue
                        if isinstance(item, dict) and "__terminal__" in item:
                            if item.get("__terminal__") == "error":
                                failure_type = item.get("failure_type")
                                failure_type_value = (
                                    failure_type
                                    if isinstance(failure_type, str) and failure_type
                                    else "runtime_error"
                                )
                                self._agent_run_failures_total.add(
                                    1,
                                    {"entrypoint": "run_stream", "failure_type": failure_type_value},
                                )
                            persistence, events = terminal_stream_events(
                                terminal_item=item,
                                session_id=session_id,
                                run_id=run_id,
                                token_emitted=token_emitted,
                                chunk_text=self._chunk_text,
                            )
                            self._message_repo.create(
                                models.Message(
                                    id=str(uuid4()),
                                    session_id=session_id,
                                    role="assistant",
                                    content=persistence["message"],
                                    created_at=datetime.now(timezone.utc),
                                    metadata_json=(
                                        {**(persistence["metadata"] or {}), "run_id": run_id}
                                        if isinstance(persistence["metadata"], dict)
                                        or persistence["metadata"] is None
                                        else {"run_id": run_id}
                                    ),
                                )
                            )
                            for event in events:
                                yield event
                            break
                        if item is done:
                            break
                        if item.get("type") == "assistant.token.delta":
                            token_emitted = True
                        yield item
            finally:
                self._agent_run_duration_ms.record(
                    (time.perf_counter() - started) * 1000.0,
                    {"entrypoint": "run_stream"},
                )
                self._logger.info(
                    "chat stream finished",
                )
                clear_log_context()

        return _stream()
