from dataclasses import dataclass
from typing import Any


@dataclass
class SpanAttributes:
    model_id: str
    agent_node: str
    tokens_input: int
    tokens_output: int
    cost_usd: float
    session_id: str
    agent_run_id: str


def build_span_attributes(
    model_id: str,
    agent_node: str,
    tokens_input: int,
    tokens_output: int,
    cost_usd: float,
    session_id: str,
    agent_run_id: str,
) -> dict[str, Any]:
    return {
        "model_id": model_id,
        "agent_node": agent_node,
        "tokens_input": tokens_input,
        "tokens_output": tokens_output,
        "cost_usd": cost_usd,
        "session_id": session_id,
        "agent_run_id": agent_run_id,
    }
