from __future__ import annotations

import json

from opscopilot_agent_runtime.llm.answer import AnswerSynthesizer
from opscopilot_agent_runtime.state import AgentState


def _read_prompt(state: AgentState) -> str:
    prompt = state.prompt
    if not prompt:
        raise RuntimeError("prompt required")
    return prompt


def _read_tool_results(state: AgentState) -> list:
    results = state.tool_results
    if not results:
        raise RuntimeError("tool_results required")
    return results


class AnswerNode:
    def __init__(self, synthesizer: AnswerSynthesizer | None = None) -> None:
        self._synthesizer = synthesizer

    @staticmethod
    def _sanitize_value(value, max_str_len: int, max_list_len: int) -> tuple[object, int]:
        if isinstance(value, str):
            if len(value) <= max_str_len:
                return value, len(value)
            return f"{value[:max_str_len]}…<truncated>", max_str_len
        if isinstance(value, list):
            total = 0
            out = []
            for item in value[:max_list_len]:
                sanitized, size = AnswerNode._sanitize_value(item, max_str_len, max_list_len)
                out.append(sanitized)
                total += size
            if len(value) > max_list_len:
                out.append("…<truncated list>")
            return out, total
        if isinstance(value, dict):
            total = 0
            out = {}
            for key, item in value.items():
                sanitized, size = AnswerNode._sanitize_value(item, max_str_len, max_list_len)
                out[key] = sanitized
                total += size
            return out, total
        return value, 0

    @staticmethod
    def _sanitize_tool_results(results: list, max_chars: int = 2000, max_str_len: int = 500, max_list_len: int = 50) -> list:
        sanitized_results = []
        running = 0
        for result in results:
            payload = getattr(result, "result", None)
            if payload is None and isinstance(result, dict):
                payload = result.get("result")
            if payload is None:
                sanitized_results.append(result)
                continue
            sanitized, size = AnswerNode._sanitize_value(payload, max_str_len, max_list_len)
            running += size
            if running > max_chars:
                sanitized = {"notice": "tool output omitted (size limit)"}
            if hasattr(result, "result"):
                sanitized_results.append(result.__class__(
                    step_id=result.step_id,
                    tool_name=result.tool_name,
                    result=sanitized,
                ))
            else:
                sanitized_results.append(sanitized)
        return sanitized_results

    def __call__(self, state: AgentState) -> AgentState:
        if state.error:
            return state
        if self._synthesizer is None:
            raise RuntimeError("answer_synthesizer_missing")
        prompt = _read_prompt(state)
        results = state.tool_results
        if not results:
            if state.rag is None:
                raise RuntimeError("tool_results required")
            results = []
        llm_results = self._sanitize_tool_results(results)
        answer = self._synthesizer.synthesize(
            prompt,
            llm_results,
            rag_context=state.rag.text if state.rag else None,
            recorder=state.recorder,
        )
        return state.merge(answer=answer, citations=state.rag.citations if state.rag else None)
