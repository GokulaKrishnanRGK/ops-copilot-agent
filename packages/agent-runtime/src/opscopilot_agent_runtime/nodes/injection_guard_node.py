from __future__ import annotations

import re

from opscopilot_agent_runtime.runtime.events import AgentEvent
from opscopilot_agent_runtime.runtime.logging import get_logger
from opscopilot_agent_runtime.state import AgentState

_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(previous|prior|all)\s+(instructions?|directives?|rules?|context)", re.IGNORECASE),
    re.compile(r"forget\s+(previous|prior|all)\s+(instructions?|directives?|rules?|context)", re.IGNORECASE),
    re.compile(r"disregard\s+(previous|prior|all)\s+(instructions?|directives?|rules?|context)", re.IGNORECASE),
    re.compile(r"override\s+(previous|prior|all|your)\s+(instructions?|directives?|rules?|constraints?)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an|the)\b", re.IGNORECASE),
    re.compile(r"\bact\s+as\s+(a|an)\b", re.IGNORECASE),
    re.compile(r"\bpretend\s+(you\s+are|to\s+be)\b", re.IGNORECASE),
    re.compile(r"<INST>", re.IGNORECASE),
    re.compile(r"\[INST\]", re.IGNORECASE),
    re.compile(r"<system>", re.IGNORECASE),
    re.compile(r"\n\s*Human\s*:", re.IGNORECASE),
    re.compile(r"\n\s*Assistant\s*:", re.IGNORECASE),
    re.compile(r"###\s*System\b", re.IGNORECASE),
    re.compile(r"###\s*Instruction\b", re.IGNORECASE),
]

_REJECTION_MESSAGE = "This request cannot be processed."


class PromptInjectionGuard:
    def __init__(self, patterns: list[re.Pattern[str]] | None = None) -> None:
        self._patterns = patterns if patterns is not None else _PATTERNS

    def __call__(self, state: AgentState) -> AgentState:
        if state.error or not state.prompt:
            return state
        logger = get_logger(__name__)
        for pattern in self._patterns:
            if pattern.search(state.prompt):
                logger.warning("injection_guard: blocked pattern=%s", pattern.pattern)
                return state.merge(
                    answer=_REJECTION_MESSAGE,
                    event=AgentEvent(
                        event_type="injection_guard.blocked",
                        payload={"pattern": pattern.pattern},
                    ),
                    error={
                        "type": "injection_detected",
                        "message": _REJECTION_MESSAGE,
                    },
                )
        return state
