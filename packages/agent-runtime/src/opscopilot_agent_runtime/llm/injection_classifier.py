from __future__ import annotations

import uuid

from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider
from opscopilot_llm_gateway.types import LlmMessage, LlmRequest, LlmResponseFormat, LlmTags

from opscopilot_agent_runtime.persistence import AgentRunRecorder
from opscopilot_agent_runtime.prompts import LocalYamlPromptSource, PromptSource, prompt_ref_for

from .base import LlmNodeBase


def _schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "is_injection": {"type": "boolean"},
        },
        "required": ["is_injection"],
    }


class LlmInjectionClassifier(LlmNodeBase):
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

    def classify(self, prompt: str, recorder: AgentRunRecorder | None = None) -> bool:
        system_prompt = self._prompt_source.get("injection_classifier", self._prompt_version)
        request = LlmRequest(
            model_id=self._model_id,
            messages=[
                LlmMessage(role="system", content=system_prompt),
                LlmMessage(role="user", content=prompt),
            ],
            response_format=LlmResponseFormat(type="json_schema", schema=_schema()),
            temperature=0.0,
            max_tokens=64,
            idempotency_key=str(uuid.uuid4()),
            tags=LlmTags(
                session_id="injection_guard",
                agent_run_id="injection_guard",
                agent_node="injection_classifier",
            ),
            prompt_ref=prompt_ref_for(self._prompt_source, "injection_classifier", self._prompt_version),
        )
        response = self._call(
            request=request,
            agent_node="injection_classifier",
            recorder=recorder or self._recorder,
        )
        if response.error:
            return False
        payload = response.output.json or {}
        return bool(payload.get("is_injection", False))
