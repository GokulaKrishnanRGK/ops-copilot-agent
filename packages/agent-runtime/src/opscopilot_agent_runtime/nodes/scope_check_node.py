from __future__ import annotations

from opscopilot_agent_runtime.llm.scope import ScopeClassifier
from opscopilot_agent_runtime.runtime.events import AgentEvent
from opscopilot_agent_runtime.runtime.logging import get_logger
from opscopilot_agent_runtime.state import AgentState


class ScopeCheckNode:
    def __init__(self, classifier: ScopeClassifier | None = None) -> None:
        self._classifier = classifier

    def __call__(self, state: AgentState) -> AgentState:
        if state.error:
            return state
        if self._classifier is None or not state.prompt:
            return state
        logger = get_logger(__name__)
        logger.debug("scope_check: prompt_present=%s", bool(state.prompt))
        tools = state.tools or []
        tool_names = [tool.name for tool in tools]
        on_delta = None
        if state.llm_stream_callback is not None:
            on_delta = lambda text: state.llm_stream_callback("scope", text)
        payload = self._classifier.classify(
            state.prompt,
            tool_names,
            recorder=state.recorder,
            on_delta=on_delta,
        )
        allowed = payload.get("allowed", True)
        response = payload.get("response") or "This request is outside the supported scope."
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
