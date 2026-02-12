from __future__ import annotations

import json
import os

from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer
from opscopilot_llm_gateway.costs import estimate_cost_usd
from opscopilot_llm_gateway.gateway import run_gateway_call
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider
from opscopilot_llm_gateway.types import LlmRequest

from opscopilot_agent_runtime.persistence import AgentRunRecorder
from opscopilot_agent_runtime.runtime.logging import get_logger


class LlmNodeBase:
    def __init__(
        self,
        provider: BedrockProvider,
        model_id: str,
        cost_table: dict,
        budget: BudgetEnforcer,
        ledger: CostLedger,
    ) -> None:
        self._provider = provider
        self._model_id = model_id
        self._cost_table = cost_table
        self._budget = budget
        self._ledger = ledger

    def _call(
        self,
        request: LlmRequest,
        agent_node: str,
        recorder: AgentRunRecorder | None,
    ):
        logger = get_logger(__name__)
        if os.getenv("AGENT_DEBUG") == "1" or os.getenv("LLM_DEBUG") == "1":
            logger.info(
                "llm request node=%s model=%s messages=%s",
                agent_node,
                request.model_id,
                json.dumps([m.content for m in request.messages], default=str),
            )
        response = run_gateway_call(
            provider=self._provider,
            request=request,
            cost_table=self._cost_table,
            budget=self._budget,
            ledger=self._ledger,
        )
        cost_usd = estimate_cost_usd(
            self._cost_table,
            self._model_id,
            response.tokens_input,
            response.tokens_output,
        )
        if os.getenv("AGENT_DEBUG") == "1" or os.getenv("LLM_DEBUG") == "1":
            logger.info(
                "llm response node=%s tokens_in=%s tokens_out=%s cost_usd=%s error=%s output=%s",
                agent_node,
                response.tokens_input,
                response.tokens_output,
                cost_usd,
                getattr(response.error, "message", None),
                json.dumps(response.output.json, default=str),
            )
        if recorder:
            recorder.record_llm_call(
                agent_node=agent_node,
                model_id=self._model_id,
                tokens_input=response.tokens_input,
                tokens_output=response.tokens_output,
                cost_usd=cost_usd,
                latency_ms=response.latency_ms,
                metadata_json=response.provider_metadata,
            )
            recorder.record_budget_event(
                kind="llm_call",
                delta_usd=cost_usd,
                total_usd=self._budget.state().total_usd,
            )
        return response
