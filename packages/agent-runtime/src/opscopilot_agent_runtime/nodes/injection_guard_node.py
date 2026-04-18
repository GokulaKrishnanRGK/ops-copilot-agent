from __future__ import annotations

import re
from typing import Protocol, runtime_checkable

from opscopilot_agent_runtime.persistence import AgentRunRecorder
from opscopilot_agent_runtime.runtime.events import AgentEvent
from opscopilot_agent_runtime.runtime.logging import get_logger
from opscopilot_agent_runtime.state import AgentState

_logger = get_logger(__name__)


@runtime_checkable
class InjectionClassifier(Protocol):
    def classify(self, prompt: str, recorder: AgentRunRecorder | None = None) -> bool: ...


class StubInjectionClassifier:
    def classify(self, prompt: str, recorder: AgentRunRecorder | None = None) -> bool:
        return False

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
    def __init__(
        self,
        patterns: list[re.Pattern[str]] | None = None,
        classifier: InjectionClassifier | None = None,
    ) -> None:
        self._patterns = patterns if patterns is not None else _PATTERNS
        self._classifier = classifier

    def __call__(self, state: AgentState) -> AgentState:
        if state.error or not state.prompt:
            _logger.debug("injection_guard: skipped error=%s prompt_present=%s", bool(state.error), bool(state.prompt))
            return state
        scan_target = state.user_prompt if state.user_prompt is not None else state.prompt
        _logger.debug("injection_guard: enter prompt_len=%d scan_len=%d", len(state.prompt), len(scan_target))
        for pattern in self._patterns:
            if pattern.search(scan_target):
                _logger.warning("injection_guard: blocked layer=regex pattern=%s", pattern.pattern)
                return state.merge(
                    answer=_REJECTION_MESSAGE,
                    event=AgentEvent(
                        event_type="injection_guard.blocked",
                        payload={"pattern": pattern.pattern, "layer": "regex"},
                    ),
                    error={
                        "type": "injection_detected",
                        "message": _REJECTION_MESSAGE,
                    },
                )
        if self._classifier is not None and self._classifier.classify(scan_target, recorder=state.recorder):
            _logger.warning("injection_guard: blocked layer=llm_classifier")
            return state.merge(
                answer=_REJECTION_MESSAGE,
                event=AgentEvent(
                    event_type="injection_guard.blocked",
                    payload={"pattern": "llm_classifier", "layer": "llm_classifier"},
                ),
                error={
                    "type": "injection_detected",
                    "message": _REJECTION_MESSAGE,
                },
            )
        _logger.debug(
            "injection_guard: passed pattern_count=%d classifier_present=%s",
            len(self._patterns),
            self._classifier is not None,
        )
        return state
