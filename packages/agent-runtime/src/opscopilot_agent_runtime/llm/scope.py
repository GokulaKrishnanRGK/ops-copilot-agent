from __future__ import annotations

import json
import os
import uuid
from typing import Callable

from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider
from opscopilot_llm_gateway.types import LlmMessage, LlmRequest, LlmResponseFormat, LlmTags

from opscopilot_agent_runtime.persistence import AgentRunRecorder
from opscopilot_agent_runtime.prompts import LocalYamlPromptSource, PromptSource, prompt_ref_for

from .base import LlmNodeBase


def _read_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _scope_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "allowed": {"type": "boolean"},
            "response": {"type": "string"},
        },
        "required": ["allowed", "response"],
    }


class ScopeClassifier(LlmNodeBase):
    def __init__(
        self,
        provider: BedrockProvider,
        model_id: str,
        budget: BudgetEnforcer,
        ledger: CostLedger,
        recorder: AgentRunRecorder | None = None,
        prompt_source: PromptSource | None = None,
        prompt_version: str = "v1",
    ) -> None:
        super().__init__(provider, model_id, budget, ledger)
        self._recorder = recorder
        self._prompt_source = prompt_source or LocalYamlPromptSource()
        self._prompt_version = prompt_version

    @staticmethod
    def from_env(
        provider: BedrockProvider,
        budget: BudgetEnforcer,
        ledger: CostLedger,
        recorder: AgentRunRecorder | None = None,
        prompt_source: PromptSource | None = None,
    ) -> "ScopeClassifier":
        model_id = _read_env("SCOPE_MODEL_ID")
        prompt_version = os.getenv("SCOPE_PROMPT_VERSION", "v1")
        return ScopeClassifier(
            provider,
            model_id,
            budget,
            ledger,
            recorder=recorder,
            prompt_source=prompt_source,
            prompt_version=prompt_version,
        )

    def classify(
        self,
        prompt: str,
        tool_names: list[str],
        rag_context: str | None = None,
        recorder: AgentRunRecorder | None = None,
        on_delta: Callable[[str], None] | None = None,
    ) -> dict:
        system_prompt = self._prompt_source.get("scope", self._prompt_version)
        payload = {"prompt": prompt, "tools": tool_names}
        if rag_context:
            payload["rag_context"] = rag_context
        request = LlmRequest(
            model_id=self._model_id,
            messages=[
                LlmMessage(role="system", content=system_prompt),
                LlmMessage(
                    role="user",
                    content=json.dumps(payload),
                ),
            ],
            response_format=LlmResponseFormat(type="json_schema", schema=_scope_schema()),
            temperature=0.0,
            max_tokens=128,
            idempotency_key=str(uuid.uuid4()),
            tags=LlmTags(session_id="scope", agent_run_id="scope", agent_node="scope"),
            prompt_ref=prompt_ref_for(self._prompt_source, "scope", self._prompt_version),
        )
        response = self._call(
            request=request,
            agent_node="scope",
            recorder=recorder or self._recorder,
            on_delta=on_delta,
        )
        if response.error:
            raise RuntimeError(response.error.message)
        return response.output.json or {}
