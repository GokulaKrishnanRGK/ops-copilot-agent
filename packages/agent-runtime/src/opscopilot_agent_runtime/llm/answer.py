from __future__ import annotations

import json
import uuid
from typing import Callable

from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider
from opscopilot_llm_gateway.types import (
    LlmMessage,
    LlmRequest,
    LlmResponseFormat,
    LlmTags,
)

from opscopilot_agent_runtime.persistence import AgentRunRecorder
from opscopilot_agent_runtime.prompts import LocalYamlPromptSource, PromptSource, prompt_ref_for

from .base import LlmNodeBase
from .spotlight import wrap_tool_result, wrap_user_input


def _response_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
        },
        "required": ["answer"],
    }


def _tool_summary(tool_results: list) -> str:
    def sanitize(value):
        if isinstance(value, str):
            if len(value) > 400:
                return "<omitted>"
            return value
        if isinstance(value, list):
            return [sanitize(item) for item in value]
        if isinstance(value, dict):
            return {key: sanitize(item) for key, item in value.items()}
        return value

    lines = []
    for result in tool_results:
        tool_name = getattr(result, "tool_name", None)
        tool_result = getattr(result, "result", None)
        if tool_name is None and isinstance(result, dict):
            tool_name = result.get("tool_name")
            tool_result = result.get("result")
        summarized = tool_result
        if isinstance(tool_result, dict):
            summarized = tool_result.get("structured_content", tool_result)
            if isinstance(summarized, dict) and "result" in summarized:
                result_payload = summarized.get("result")
                if isinstance(result_payload, dict) and "logs" in result_payload:
                    result_payload = dict(result_payload)
                    result_payload["logs"] = "<omitted>"
                    summarized = dict(summarized)
                    summarized["result"] = result_payload
        lines.append(f"tool={tool_name} result={json.dumps(sanitize(summarized), default=str)}")
    return "\n".join(lines)


class AnswerSynthesizer(LlmNodeBase):
    def __init__(
        self,
        provider: BedrockProvider,
        model_id: str,
        budget: BudgetEnforcer,
        ledger: CostLedger,
        recorder: AgentRunRecorder | None = None,
        prompt_source: PromptSource | None = None,
        prompt_version: str = "latest",
    ) -> None:
        super().__init__(provider, model_id, budget, ledger)
        self._recorder = recorder
        self._prompt_source = prompt_source or LocalYamlPromptSource()
        self._prompt_version = prompt_version

    def synthesize(
        self,
        prompt: str,
        tool_results: list,
        rag_context: str | None = None,
        recorder: AgentRunRecorder | None = None,
        on_delta: Callable[[str], None] | None = None,
    ) -> str:
        system_prompt = self._prompt_source.get("answer", self._prompt_version)
        context_block = f"\n\nContext:\n{rag_context}" if rag_context else ""
        user_content = (
            f"Prompt: {wrap_user_input(prompt)}{context_block}\n\nTool results:\n{wrap_tool_result(_tool_summary(tool_results))}"
        )
        if on_delta is not None:
            stream_prompt = self._prompt_source.get("answer_stream", self._prompt_version)
            request = LlmRequest(
                model_id=self._model_id,
                messages=[
                    LlmMessage(
                        role="system",
                        content=stream_prompt,
                        cache_control={"type": "ephemeral"},
                    ),
                    LlmMessage(role="user", content=user_content),
                ],
                response_format=LlmResponseFormat(type="text", schema=None),
                temperature=0.0,
                max_tokens=1024,
                idempotency_key=str(uuid.uuid4()),
                tags=LlmTags(session_id="answer", agent_run_id="answer", agent_node="answer"),
                prompt_ref=prompt_ref_for(
                    self._prompt_source,
                    "answer_stream",
                    self._prompt_version,
                ),
            )
            response = self._call(
                request=request,
                agent_node="answer",
                recorder=recorder or self._recorder,
                on_delta=on_delta,
            )
            answer_text = response.output.text or ""
            if not answer_text:
                raise RuntimeError("answer missing")
            return answer_text
        request = LlmRequest(
            model_id=self._model_id,
            messages=[
                LlmMessage(
                    role="system",
                    content=system_prompt,
                    cache_control={"type": "ephemeral"},
                ),
                LlmMessage(role="user", content=user_content),
            ],
            response_format=LlmResponseFormat(type="json_schema", schema=_response_schema()),
            temperature=0.0,
            max_tokens=1024,
            idempotency_key=str(uuid.uuid4()),
            tags=LlmTags(session_id="answer", agent_run_id="answer", agent_node="answer"),
            prompt_ref=prompt_ref_for(self._prompt_source, "answer", self._prompt_version),
        )
        response = self._call(
            request=request,
            agent_node="answer",
            recorder=recorder or self._recorder,
        )
        if response.error:
            raise RuntimeError(response.error.message)
        payload = response.output.json or {}
        answer = payload.get("answer")
        if not answer:
            raise RuntimeError("answer missing")
        return answer
