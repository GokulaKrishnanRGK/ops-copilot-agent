from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from queue import Empty, Queue
import threading
from uuid import uuid4

from opscopilot_agent_runtime.persistence import AgentRunRecorder
from opscopilot_agent_runtime.state import AgentState
from opscopilot_db import models, repositories

from .event_mapper import (
    agent_run_completed,
    agent_run_started,
)
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
            error = metadata.get("error") if isinstance(metadata, dict) else None
            is_out_of_scope = isinstance(error, dict) and error.get("type") == "out_of_scope"
            if not is_out_of_scope:
                history.append(pending_user_prompt)
            pending_user_prompt = None
        if pending_user_prompt:
            history.append(pending_user_prompt)
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

    def run(self, session_id: str, prompt: str) -> ChatResult:
        session = self._session_repo.get(session_id)
        if session is None:
            raise SessionNotFoundError("session not found")

        prompt_history = self._load_prompt_history(session_id)
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
        recorder = self._recorder_factory(session_id, run_id)
        runtime = self._runtime_factory.create(recorder=recorder)
        try:
            result = runtime.run(AgentState(prompt=prompt, prompt_history=prompt_history))
        except Exception as exc:
            raise ChatExecutionError("agent runtime failed") from exc

        answer_text = result.answer
        if answer_text is None and result.error:
            answer_text = result.error.get("message", "request failed")
        clarification = self._is_clarification(result.error)
        self._message_repo.create(
            models.Message(
                id=str(uuid4()),
                session_id=session_id,
                role="assistant",
                content=answer_text or "",
                created_at=datetime.now(timezone.utc),
                metadata_json={"clarification_required": True}
                if clarification
                else ({"error": result.error} if result.error else None),
            )
        )

        return ChatResult(
            run_id=run_id,
            answer=answer_text,
            error=None if clarification else result.error,
        )

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
                metadata_json=None,
            )
        )

        def _stream():
            yield agent_run_started(session_id, run_id)

            recorder = self._recorder_factory(session_id, run_id)
            runtime = self._runtime_factory.create(recorder=recorder)
            decider = StreamEventDecider()
            tracker = StreamLifecycleTracker()
            queue: Queue = Queue()
            done = object()

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
                    for state in runtime.run_stream(
                        AgentState(
                            prompt=prompt,
                            prompt_history=prompt_history,
                            llm_stream_callback=on_llm_delta,
                        )
                    ):
                        last_state = state
                        if state.event is not None:
                            events = decider.runtime_events(
                                session_id=session_id,
                                run_id=run_id,
                                event_type=state.event.event_type,
                                payload=state.event.payload or {},
                                tracker=tracker,
                                answer_message=state.answer,
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

            thread = threading.Thread(target=worker, daemon=True)
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
                            metadata_json=persistence["metadata"],
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

        return _stream()
