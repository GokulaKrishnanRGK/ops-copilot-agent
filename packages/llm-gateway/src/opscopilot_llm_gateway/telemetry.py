from typing import Any


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
        "gen_ai.request.model": model_id,
        "gen_ai.usage.input_tokens": tokens_input,
        "gen_ai.usage.output_tokens": tokens_output,
        "agent_node": agent_node,
        "cost_usd": cost_usd,
        "session_id": session_id,
        "agent_run_id": agent_run_id,
    }
