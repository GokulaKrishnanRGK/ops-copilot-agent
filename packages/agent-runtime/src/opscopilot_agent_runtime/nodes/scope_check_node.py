from __future__ import annotations

from opscopilot_agent_runtime.llm.scope import ScopeClassifier
from opscopilot_agent_runtime.runtime.events import AgentEvent
from opscopilot_agent_runtime.runtime.logging import get_logger
from opscopilot_agent_runtime.state import AgentState


class ScopeCheckNode:
    def __init__(self, classifier: ScopeClassifier | None = None) -> None:
        self._classifier = classifier

    def __call__(self, state: AgentState) -> AgentState:
        logger = get_logger(__name__)
        if state.error:
            logger.debug("scope_check: skipped existing_error=%s", state.error.get("type"))
            return state
        if self._classifier is None or not state.prompt:
            logger.debug("scope_check: skipped classifier_present=%s prompt_present=%s", bool(self._classifier), bool(state.prompt))
            return state
        tools = state.tools or []
        tool_descriptions = [
            f"{t.name}: {t.description}" if t.description else t.name for t in tools
        ]
        logger.debug("scope_check: enter prompt_len=%d tool_count=%d", len(state.prompt), len(tools))
        on_delta = None
        if state.llm_stream_callback is not None:
            on_delta = lambda text: state.llm_stream_callback("scope", text)
        payload = self._classifier.classify(
            state.prompt,
            tool_descriptions,
            recorder=state.recorder,
            on_delta=on_delta,
        )
        allowed = payload.get("allowed", True)
        is_greeting = payload.get("is_greeting", False)
        response = payload.get("response") or "This request is outside the supported scope."
        logger.debug("scope_check: result allowed=%s is_greeting=%s", allowed, is_greeting)
        if is_greeting:
            return state.merge(
                answer=response,
                event=AgentEvent(
                    event_type="scope_check.completed",
                    payload={"response": response},
                ),
            )
        if not allowed:
            return state.merge(
                answer=response,
                event=AgentEvent(
                    event_type="scope_check.rejected",
                    payload={"response": response},
                ),
                error={
                    "type": "out_of_scope",
                    "message": response,
                },
            )
        return state.merge(
            event=AgentEvent(
                event_type="scope_check.completed",
                payload={"response": response},
            )
        )
