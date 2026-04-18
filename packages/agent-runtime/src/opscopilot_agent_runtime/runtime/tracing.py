from __future__ import annotations

import json
import os
from contextvars import ContextVar
from typing import Any

_agent_graph_otel_ctx: ContextVar = ContextVar("_agent_graph_otel_ctx", default=None)


def _json(value: Any) -> str:
    return json.dumps(value, default=str)


def set_langfuse_env_attributes(span: Any) -> None:
    env = os.getenv("LANGFUSE_ENVIRONMENT")
    if env:
        span.set_attribute("langfuse.environment", env)
    release = os.getenv("LANGFUSE_RELEASE")
    if release:
        span.set_attribute("langfuse.release", release)


_TOOL_NODES = frozenset({"tool_executor"})


def set_node_observation_attributes(
    span: Any,
    state_in: Any,
    state_out: Any,
    node_name: str,
    elapsed_ms: float,
) -> None:
    obs_type = "tool" if node_name in _TOOL_NODES else "span"
    span.set_attribute("langfuse.observation.type", obs_type)

    recorder = getattr(state_in, "recorder", None)
    if recorder:
        span.set_attribute("session.id", recorder.session_id)

    prompt = getattr(state_in, "user_prompt", None) or getattr(state_in, "prompt", None) or ""
    input_data: dict[str, Any] = {"prompt": prompt[:1000]}
    tools = getattr(state_in, "tools", None)
    if tools:
        input_data["tool_count"] = len(tools)
    span.set_attribute("langfuse.observation.input", _json(input_data))

    output_data: dict[str, Any] = {}
    event = getattr(state_out, "event", None)
    if event:
        output_data["event"] = event.event_type
    answer = getattr(state_out, "answer", None)
    if answer:
        output_data["answer"] = answer[:500]
    error_out = getattr(state_out, "error", None)
    if error_out:
        output_data["error"] = error_out
    span.set_attribute("langfuse.observation.output", _json(output_data))

    metadata: dict[str, Any] = {"node": node_name, "elapsed_ms": round(elapsed_ms, 1)}
    plan = getattr(state_out, "plan", None)
    if plan and hasattr(plan, "steps"):
        metadata["plan_steps"] = len(plan.steps)
    tool_results = getattr(state_out, "tool_results", None)
    if tool_results:
        metadata["tool_results"] = len(tool_results)
    span.set_attribute("langfuse.observation.metadata", _json(metadata))

    set_langfuse_env_attributes(span)
