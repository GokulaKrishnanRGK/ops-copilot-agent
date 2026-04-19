from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider
from opscopilot_llm_gateway.types import LlmMessage, LlmRequest, LlmResponseFormat, LlmTags

from .base import LlmNodeBase

_SYSTEM_PROMPT = (
    "Generate a concise title for a conversation that starts with the user message below.\n"
    "Rules:\n"
    "- 3 to 6 words maximum\n"
    "- Return only the title, nothing else\n"
    "- No quotes, no period at the end\n"
    "- Use title case"
)


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
    ) -> None:
        super().__init__(provider, model_id, budget, ledger)

    def generate(self, prompt: str, session_id: str, run_id: str) -> str:
        with self._tracer.start_as_current_span("title-gen") as span:
            span.set_attribute("langfuse.trace.name", "title-gen")
            span.set_attribute("langfuse.trace.input", prompt[:500])
            span.set_attribute("langfuse.observation.type", "span")
            request = LlmRequest(
                model_id=self._model_id,
                messages=[
                    LlmMessage(role="system", content=_SYSTEM_PROMPT),
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
            )
            response = self._call(request=request, agent_node="title_gen", recorder=None)
            if response.error or response.output is None:
                span.set_attribute("langfuse.trace.output", "")
                return ""
            title = (response.output.text or "").strip().strip('"\'')
            span.set_attribute("langfuse.trace.output", title)
            return title
