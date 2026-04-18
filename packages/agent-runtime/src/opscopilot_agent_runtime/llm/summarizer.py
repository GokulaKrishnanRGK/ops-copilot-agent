from __future__ import annotations

import uuid

from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider
from opscopilot_llm_gateway.types import LlmMessage, LlmRequest, LlmResponseFormat, LlmTags

from opscopilot_agent_runtime.persistence import AgentRunRecorder
from opscopilot_agent_runtime.prompts import LocalYamlPromptSource, PromptSource, prompt_ref_for
from opscopilot_agent_runtime.llm.spotlight import wrap_user_input

from .base import LlmNodeBase


class SummarizerLlmNode(LlmNodeBase):
    def __init__(
        self,
        provider: BedrockProvider,
        model_id: str,
        budget: BudgetEnforcer,
        ledger: CostLedger,
        prompt_source: PromptSource | None = None,
        prompt_version: str = "latest",
    ) -> None:
        super().__init__(provider, model_id, budget, ledger)
        self._prompt_source = prompt_source or LocalYamlPromptSource()
        self._prompt_version = prompt_version

    def summarize(
        self,
        older_turns: list[str],
        existing_summary: str | None = None,
        log_excerpts: list[str] | None = None,
        recorder: AgentRunRecorder | None = None,
    ) -> str:
        system_prompt = self._prompt_source.get("summarizer", self._prompt_version)
        parts: list[str] = []
        if existing_summary:
            parts.append(f"[PREVIOUS SUMMARY]\n{existing_summary}")
        parts.append("[CONVERSATION TURNS]\n" + "\n".join(older_turns))
        if log_excerpts:
            parts.append("[LOG EXCERPTS]\n" + "\n".join(log_excerpts))
        user_content = wrap_user_input("\n\n".join(parts))
        request = LlmRequest(
            model_id=self._model_id,
            messages=[
                LlmMessage(role="system", content=system_prompt, cache_control={"type": "ephemeral"}),
                LlmMessage(role="user", content=user_content),
            ],
            response_format=LlmResponseFormat(type="text", schema=None),
            temperature=0.0,
            max_tokens=256,
            idempotency_key=str(uuid.uuid4()),
            tags=LlmTags(
                session_id="summarizer",
                agent_run_id="summarizer",
                agent_node="summarizer",
            ),
            prompt_ref=prompt_ref_for(self._prompt_source, "summarizer", self._prompt_version),
        )
        response = self._call(request=request, agent_node="summarizer", recorder=recorder)
        if response.error or response.output is None:
            return existing_summary or ""
        return (response.output.text or "").strip()
