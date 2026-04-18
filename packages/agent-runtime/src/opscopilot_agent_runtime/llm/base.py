from __future__ import annotations

import json
import os
from dataclasses import replace
from typing import Callable

from opentelemetry import metrics, trace
from opscopilot_llm_gateway.accounting import CostLedger
from opscopilot_llm_gateway.budgets import BudgetEnforcer
from opscopilot_llm_gateway.gateway import run_gateway_call
from opscopilot_llm_gateway.providers.bedrock import BedrockProvider
from opscopilot_llm_gateway.types import LlmRequest, LlmResponse, LlmTags

from opscopilot_agent_runtime.persistence import AgentRunRecorder
from opscopilot_agent_runtime.runtime.logging import get_logger


def _emit_get_prompt_span(tracer: object, request: LlmRequest) -> None:
    prompt_ref = request.prompt_ref
    if prompt_ref is None:
        return
    system_content = next(
        (m.content for m in request.messages if m.role == "system"),
        "",
    )
    with tracer.start_as_current_span("get-langfuse-prompt") as ps:  # type: ignore[union-attr]
        ps.set_attribute("langfuse.observation.type", "span")
        ps.set_attribute(
            "langfuse.observation.input",
            json.dumps([prompt_ref.name, {"version": prompt_ref.version}]),
        )
        ps.set_attribute(
            "langfuse.observation.output",
            json.dumps(system_content if isinstance(system_content, str) else str(system_content)),
        )
        ps.set_attribute("langfuse.observation.prompt.name", prompt_ref.name)
        ps.set_attribute(
            "langfuse.observation.prompt.version",
            prompt_ref.langfuse_version or prompt_ref.version,
        )
        ps.set_attribute("prompt.name", prompt_ref.name)
        ps.set_attribute("prompt.version", prompt_ref.langfuse_version or prompt_ref.version)


def _span_safe(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in value)


def _node_span_name(agent_node: str) -> str:
    return f"llm.node.{_span_safe(agent_node)}"


def _set_llm_generation_attributes(span: object, request: LlmRequest, response: LlmResponse) -> None:
    span.set_attribute("langfuse.observation.type", "generation")  # type: ignore[union-attr]
    span.set_attribute("langfuse.observation.model.name", request.model_id)  # type: ignore[union-attr]
    span.set_attribute(  # type: ignore[union-attr]
        "langfuse.observation.model.parameters",
        json.dumps({"temperature": request.temperature, "max_tokens": request.max_tokens}),
    )
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    span.set_attribute("langfuse.observation.input", json.dumps(messages, default=str))  # type: ignore[union-attr]
    output_payload = response.output.json if response.output.type == "json" else response.output.text
    span.set_attribute("langfuse.observation.output", json.dumps(output_payload, default=str))  # type: ignore[union-attr]
    span.set_attribute(  # type: ignore[union-attr]
        "langfuse.observation.usage_details",
        json.dumps({
            "input": response.tokens_input,
            "output": response.tokens_output,
            "total": response.tokens_input + response.tokens_output,
            "cache_read_input_tokens": response.cache_read_input_tokens,
        }),
    )
    span.set_attribute(  # type: ignore[union-attr]
        "langfuse.observation.cost_details",
        json.dumps({"total": response.cost_usd}),
    )
    if request.prompt_ref is not None:
        span.set_attribute("langfuse.observation.prompt.name", request.prompt_ref.name)  # type: ignore[union-attr]
        span.set_attribute(  # type: ignore[union-attr]
            "langfuse.observation.prompt.version",
            request.prompt_ref.langfuse_version or request.prompt_ref.version,
        )
    if response.finish_reason:
        span.set_attribute("ai.response.finishReason", response.finish_reason)  # type: ignore[union-attr]
    first_token_ms = response.provider_metadata.get("time_to_first_token_ms")
    if first_token_ms is not None:
        span.set_attribute("ai.response.msToFirstChunk", int(first_token_ms))  # type: ignore[union-attr]
    span.set_attribute("ai.response.msToFinish", response.latency_ms)  # type: ignore[union-attr]
    if response.tokens_output > 0 and response.latency_ms > 0:
        span.set_attribute(  # type: ignore[union-attr]
            "ai.response.avgOutputTokensPerSecond",
            round(response.tokens_output / (response.latency_ms / 1000.0), 2),
        )
    span.set_attribute("ai.usage.inputTokens", response.tokens_input)  # type: ignore[union-attr]
    span.set_attribute("ai.usage.outputTokens", response.tokens_output)  # type: ignore[union-attr]
    if response.cache_read_input_tokens > 0:
        span.set_attribute(  # type: ignore[union-attr]
            "ai.usage.inputTokenDetails.cacheReadTokens", response.cache_read_input_tokens
        )
    env = os.getenv("LANGFUSE_ENVIRONMENT")
    if env:
        span.set_attribute("langfuse.environment", env)  # type: ignore[union-attr]
    release = os.getenv("LANGFUSE_RELEASE")
    if release:
        span.set_attribute("langfuse.release", release)  # type: ignore[union-attr]


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
        self._llm_cache_hits_total = meter.create_counter("llm_cache_hits_total")

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
        if effective_request.prompt_ref is not None:
            _emit_get_prompt_span(self._tracer, effective_request)
        with self._tracer.start_as_current_span(_node_span_name(agent_node)) as span:
            span.set_attribute("model_id", effective_request.model_id)
            span.set_attribute("agent_node", agent_node)
            span.set_attribute("session.id", effective_request.tags.session_id)
            span.set_attribute("agent_run_id", effective_request.tags.agent_run_id)
            response = run_gateway_call(
                provider=self._provider,
                request=effective_request,
                budget=self._budget,
                ledger=self._ledger,
                on_delta=on_delta,
            )
            _set_llm_generation_attributes(span, effective_request, response)
            cost_usd = response.cost_usd
            span.set_attribute("gen_ai.usage.input_tokens", response.tokens_input)
            span.set_attribute("gen_ai.usage.output_tokens", response.tokens_output)
            span.set_attribute("gen_ai.cache.hit", response.cache_hit)
            span.set_attribute("gen_ai.cache.read_input_tokens", response.cache_read_input_tokens)
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
            if response.cache_hit:
                self._llm_cache_hits_total.add(1, metric_attrs)
        if recorder:
            recorder.record_llm_call(
                agent_node=agent_node,
                model_id=self._model_id,
                tokens_input=response.tokens_input,
                tokens_output=response.tokens_output,
                cost_usd=cost_usd,
                latency_ms=response.latency_ms,
                metadata_json={
                    **(response.provider_metadata or {}),
                    "cache_hit": response.cache_hit,
                    "cache_read_input_tokens": response.cache_read_input_tokens,
                },
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
