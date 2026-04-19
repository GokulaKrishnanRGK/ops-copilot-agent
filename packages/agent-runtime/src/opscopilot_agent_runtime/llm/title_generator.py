from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider
from opscopilot_llm_gateway.types import LlmMessage, LlmRequest, LlmResponseFormat, LlmTags

from opscopilot_agent_runtime.prompts import LocalYamlPromptSource, PromptSource, prompt_ref_for

from .base import LlmNodeBase


@runtime_checkable
class TitleGenerator(Protocol):
    def generate(self, prompt: str, session_id: str, run_id: str) -> str: ...


class NoOpTitleGenerator:
    def generate(self, prompt: str, session_id: str, run_id: str) -> str:
        return ""


class LlmTitleGenerator(LlmNodeBase):
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

    def generate(self, prompt: str, session_id: str, run_id: str) -> str:
        system_prompt = self._prompt_source.get("title_gen", self._prompt_version)
        with self._tracer.start_as_current_span("title-gen") as span:
            span.set_attribute("langfuse.trace.name", "title-gen")
            span.set_attribute("langfuse.trace.input", prompt[:500])
            span.set_attribute("langfuse.observation.type", "span")
            request = LlmRequest(
                model_id=self._model_id,
                messages=[
                    LlmMessage(role="system", content=system_prompt),
                    LlmMessage(role="user", content=prompt[:500]),
                ],
                response_format=LlmResponseFormat(type="text", schema=None),
                temperature=0.3,
                max_tokens=20,
                idempotency_key=str(uuid.uuid4()),
                tags=LlmTags(
                    session_id=session_id,
                    agent_run_id=run_id,
                    agent_node="title_gen",
                ),
                prompt_ref=prompt_ref_for(self._prompt_source, "title_gen", self._prompt_version),
            )
            response = self._call(request=request, agent_node="title_gen", recorder=None)
            if response.error or response.output is None:
                span.set_attribute("langfuse.trace.output", "")
                return ""
            title = (response.output.text or "").strip().strip('"\'')
            span.set_attribute("langfuse.trace.output", title)
            return title
