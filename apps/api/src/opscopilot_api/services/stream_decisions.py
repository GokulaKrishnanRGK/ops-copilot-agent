from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from opscopilot_agent_runtime.state import AgentState

from .event_mapper import agent_run_completed, agent_run_failed, assistant_delta, error_event, runtime_event


@dataclass
class StreamLifecycleTracker:
    scope_started_emitted: bool = False
    planner_started_emitted: bool = False
    clarifier_started_emitted: bool = False
    answer_started_emitted: bool = False


class StreamEventDecider:
    def __init__(self) -> None:
        self._user_delta_nodes = {"answer", "clarifier_question"}

    def llm_delta_events(
        self,
        session_id: str,
        run_id: str,
        node: str,
        text: str,
        tracker: StreamLifecycleTracker,
    ) -> list[dict]:
        events: list[dict] = []
        if node not in self._user_delta_nodes:
            return events
        if node == "answer" and not tracker.answer_started_emitted:
            tracker.answer_started_emitted = True
            events.append(runtime_event(session_id, run_id, "answer.started", {}))
        events.append(assistant_delta(session_id, run_id, text, source=node))
        return events

    def runtime_events(
        self,
        session_id: str,
        run_id: str,
        event_type: str,
        payload: dict,
        tracker: StreamLifecycleTracker,
        answer_message: str | None = None,
    ) -> list[dict]:
        events: list[dict] = []
        if event_type in {"scope_check.completed", "scope_check.rejected"}:
            if not tracker.scope_started_emitted:
                tracker.scope_started_emitted = True
                events.append(runtime_event(session_id, run_id, "scope_check.started", {}))
            events.append(runtime_event(session_id, run_id, event_type, {}))
        if event_type == "planner.completed":
            if not tracker.planner_started_emitted:
                tracker.planner_started_emitted = True
                events.append(runtime_event(session_id, run_id, "planner.started", {}))
            events.append(runtime_event(session_id, run_id, event_type, {}))
        if event_type in {"clarifier.completed", "clarifier.clarification_required"}:
            if not tracker.clarifier_started_emitted:
                tracker.clarifier_started_emitted = True
                events.append(runtime_event(session_id, run_id, "clarifier.started", {}))
            if event_type == "clarifier.completed":
                events.append(runtime_event(session_id, run_id, event_type, {}))
            else:
                events.append(runtime_event(session_id, run_id, event_type, payload))
        if event_type == "answer.completed":
            if not tracker.answer_started_emitted:
                tracker.answer_started_emitted = True
                events.append(runtime_event(session_id, run_id, "answer.started", {}))
            events.append(
                runtime_event(
                    session_id,
                    run_id,
                    "answer.completed",
                    {"message": answer_message or ""},
                )
            )
        return events


def terminal_item_from_state(
    state: AgentState,
    answer_emitted: bool,
    is_clarification: Callable[[dict | None], bool],
) -> tuple[dict | None, bool]:
    if state.error:
        error_message = state.error.get("message", "request failed")
        if is_clarification(state.error):
            return {"__terminal__": "clarification", "message": error_message}, answer_emitted
        failure_type = state.error.get("type", "runtime_error")
        return (
            {
                "__terminal__": "error",
                "message": error_message,
                "failure_type": failure_type,
                "context": state.error,
            },
            answer_emitted,
        )
    if state.answer and not answer_emitted:
        return {"__terminal__": "answer", "message": state.answer}, True
    return None, answer_emitted


def terminal_stream_events(
    terminal_item: dict,
    session_id: str,
    run_id: str,
    token_emitted: bool,
    chunk_text: Callable[[str], list[str]],
) -> tuple[dict, list[dict]]:
    terminal_type = terminal_item.get("__terminal__")
    message = terminal_item.get("message", "")
    if terminal_type == "clarification":
        events: list[dict] = []
        if not token_emitted:
            for chunk in chunk_text(message):
                events.append(assistant_delta(session_id, run_id, chunk, source="clarifier"))
        events.append(agent_run_completed(session_id, run_id, "clarification_required"))
        return {"metadata": {"clarification_required": True}, "message": message}, events
    if terminal_type == "answer":
        events = []
        if not token_emitted:
            events.append(assistant_delta(session_id, run_id, message, source="answer"))
        events.append(agent_run_completed(session_id, run_id))
        return {"metadata": None, "message": message}, events

    failure_type = terminal_item.get("failure_type", "runtime_error")
    context = terminal_item.get("context")
    events = [
        error_event(session_id, run_id, failure_type, message, context),
        agent_run_failed(session_id, run_id, message, failure_type),
    ]
    return {"metadata": {"error": context}, "message": message}, events
