from __future__ import annotations

import json
import os
from dataclasses import dataclass

from opentelemetry import metrics, propagate, trace

from opscopilot_agent_runtime.mcp_client import MCPClient
from opscopilot_agent_runtime.persistence import AgentRunRecorder
from opscopilot_agent_runtime.runtime.events import AgentEvent
from opscopilot_agent_runtime.runtime.logging import get_logger
from opscopilot_agent_runtime.state import AgentState
from opscopilot_agent_runtime.nodes.planner_node import Plan


@dataclass(frozen=True)
class ToolResult:
    step_id: str
    tool_name: str
    result: dict


def _instrumented_arguments(
    args: dict,
    recorder: AgentRunRecorder | None,
) -> dict:
    next_args = dict(args)
    carrier: dict[str, str] = {}
    propagate.inject(carrier)
    traceparent = carrier.get("traceparent")
    if traceparent:
        next_args["__traceparent"] = traceparent
    tracestate = carrier.get("tracestate")
    if tracestate:
        next_args["__tracestate"] = tracestate
    if recorder:
        next_args["__session_id"] = recorder.session_id
        next_args["__agent_run_id"] = recorder.run_id
    return next_args


def execute_plan(plan: Plan, client: MCPClient, recorder: AgentRunRecorder | None = None) -> list[ToolResult]:
    logger = get_logger(__name__)
    tracer = trace.get_tracer("opscopilot_agent_runtime.tool_executor")
    meter = metrics.get_meter("opscopilot_agent_runtime.tool_executor")
    tool_calls_total = meter.create_counter("tool_calls_total")
    tool_call_errors_total = meter.create_counter("tool_call_errors_total")
    tool_call_latency_ms = meter.create_histogram("tool_call_latency_ms")
    results: list[ToolResult] = []
    for step in plan.steps:
        if os.getenv("AGENT_DEBUG") == "1":
            logger.info(
                "tool_executor step=%s tool=%s args=%s",
                step.step_id,
                step.tool_name,
                json.dumps(step.args, default=str),
            )
        with tracer.start_as_current_span("tool.call") as span:
            span.set_attribute("tool_name", step.tool_name)
            if recorder:
                span.set_attribute("session_id", recorder.session_id)
                span.set_attribute("agent_run_id", recorder.run_id)
            response = client.call_tool(
                step.tool_name,
                _instrumented_arguments(step.args, recorder),
            )
            status = response.get("structured_content", {}).get("status")
            if isinstance(status, str):
                span.set_attribute("result_status", status)
            else:
                status = "unknown"
            latency_raw = response.get("structured_content", {}).get("latency_ms", 0)
            latency_ms = latency_raw if isinstance(latency_raw, int) else 0
            metric_attrs = {"tool_name": step.tool_name, "result_status": status}
            tool_calls_total.add(1, metric_attrs)
            tool_call_latency_ms.record(latency_ms, metric_attrs)
            if status != "success":
                tool_call_errors_total.add(1, {"tool_name": step.tool_name})
        if os.getenv("AGENT_DEBUG") == "1":
            logger.info(
                "tool_executor result step=%s tool=%s response=%s",
                step.step_id,
                step.tool_name,
                json.dumps(response, default=str),
            )
        if recorder:
            recorder.record_tool_call(step.tool_name, step.args, response)
        results.append(
            ToolResult(step_id=step.step_id, tool_name=step.tool_name, result=response)
        )
    return results


class ToolExecutorNode:
    def __init__(self, client: MCPClient | None = None, recorder: AgentRunRecorder | None = None) -> None:
        self._client = client or MCPClient.from_env()
        self._recorder = recorder

    def __call__(self, state: AgentState) -> AgentState:
        if state.error:
            return state
        if state.plan is None:
            raise RuntimeError("plan_missing")
        recorder = self._recorder or state.recorder
        results = execute_plan(state.plan, self._client, recorder)
        return state.merge(
            tool_results=results,
            event=AgentEvent(event_type="tool_executor.completed", payload={"steps": len(results)}),
        )
