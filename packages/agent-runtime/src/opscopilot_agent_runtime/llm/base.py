from __future__ import annotations

from dataclasses import replace
from typing import Callable

from opentelemetry import metrics, trace
from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer
from opscopilot_llm_gateway.gateway import run_gateway_call
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider
from opscopilot_llm_gateway.types import LlmRequest, LlmTags

from opscopilot_agent_runtime.persistence import AgentRunRecorder
from opscopilot_agent_runtime.runtime.logging import get_logger


class LlmNodeBase:
    def __init__(
        self,
        provider: BedrockProvider,
        model_id: str,
        budget: BudgetEnforcer,
        ledger: CostLedger,
    ) -> None:
        self._provider = provider
        self._model_id = model_id
        self._budget = budget
        self._ledger = ledger
        self._tracer = trace.get_tracer("opscopilot_agent_runtime.llm")
        meter = metrics.get_meter("opscopilot_agent_runtime.llm")
        self._llm_calls_total = meter.create_counter("llm_calls_total")
        self._llm_tokens_input_total = meter.create_counter("llm_tokens_input_total")
        self._llm_tokens_output_total = meter.create_counter("llm_tokens_output_total")
        self._llm_cost_usd_total = meter.create_counter("llm_cost_usd_total")
        self._llm_call_latency_ms = meter.create_histogram("llm_call_latency_ms")

    def _call(
        self,
        request: LlmRequest,
        agent_node: str,
        recorder: AgentRunRecorder | None,
        on_delta: Callable[[str], None] | None = None,
    ):
        effective_request = request
        if recorder:
            effective_request = replace(
                request,
                tags=LlmTags(
                    session_id=recorder.session_id,
                    agent_run_id=recorder.run_id,
                    agent_node=agent_node,
                ),
            )
        logger = get_logger(__name__)
        with self._tracer.start_as_current_span("llm.node.call") as span:
            span.set_attribute("model_id", effective_request.model_id)
            span.set_attribute("agent_node", agent_node)
            span.set_attribute("session_id", effective_request.tags.session_id)
            span.set_attribute("agent_run_id", effective_request.tags.agent_run_id)
            response = run_gateway_call(
                provider=self._provider,
                request=effective_request,
                budget=self._budget,
                ledger=self._ledger,
                on_delta=on_delta,
            )
            cost_usd = response.cost_usd
            span.set_attribute("gen_ai.usage.input_tokens", response.tokens_input)
            span.set_attribute("gen_ai.usage.output_tokens", response.tokens_output)
            span.set_attribute("cost_usd", float(cost_usd))
            span.set_attribute("latency_ms", response.latency_ms)
            metric_attrs = {
                "agent_node": agent_node,
                "model_id": effective_request.model_id,
            }
            self._llm_calls_total.add(1, metric_attrs)
            self._llm_tokens_input_total.add(response.tokens_input, metric_attrs)
            self._llm_tokens_output_total.add(response.tokens_output, metric_attrs)
            self._llm_cost_usd_total.add(float(cost_usd), metric_attrs)
            self._llm_call_latency_ms.record(response.latency_ms, metric_attrs)
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
        logger.debug(
            "llm response node=%s tokens_in=%s tokens_out=%s cost_usd=%s error=%s",
            agent_node,
            response.tokens_input,
            response.tokens_output,
            cost_usd,
            getattr(response.error, "message", None),
        )
        return response
