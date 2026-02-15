from __future__ import annotations

from opscopilot_agent_runtime.llm.scope import ScopeClassifier
from opscopilot_agent_runtime.runtime.events import AgentEvent
from opscopilot_agent_runtime.runtime.logging import get_logger
from opscopilot_agent_runtime.runtime.rag import RagRetriever
from opscopilot_agent_runtime.state import AgentState


class ScopeCheckNode:
    def __init__(
        self,
        classifier: ScopeClassifier | None = None,
        rag_retriever: RagRetriever | None = None,
    ) -> None:
        self._classifier = classifier
        if rag_retriever is None:
            try:
                rag_retriever = RagRetriever.from_env()
            except Exception:
                rag_retriever = None
        self._rag_retriever = rag_retriever

    def __call__(self, state: AgentState) -> AgentState:
        if state.error:
            return state
        if self._classifier is None or not state.prompt:
            return state
        next_state = state
        logger = get_logger(__name__)
        logger.debug(
            "scope_check: prompt_present=%s rag_retriever=%s rag_present=%s",
            bool(next_state.prompt),
            bool(self._rag_retriever),
            bool(next_state.rag),
        )
        if next_state.prompt and self._rag_retriever and next_state.rag is None:
            try:
                logger.debug("scope_check: retrieving rag context")
                rag_context = self._rag_retriever.retrieve(
                    next_state.prompt,
                    recorder=next_state.recorder,
                )
                next_state = next_state.merge(rag=rag_context)
            except Exception:
                pass
        tools = next_state.tools or []
        tool_names = [tool.name for tool in tools]
        on_delta = None
        if next_state.llm_stream_callback is not None:
            on_delta = lambda text: next_state.llm_stream_callback("scope", text)
        payload = self._classifier.classify(
            next_state.prompt,
            tool_names,
            rag_context=next_state.rag.text if next_state.rag else None,
            recorder=next_state.recorder,
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
        return next_state.merge(
            event=AgentEvent(
                event_type="scope_check.completed",
                payload={"response": response},
            )
        )
