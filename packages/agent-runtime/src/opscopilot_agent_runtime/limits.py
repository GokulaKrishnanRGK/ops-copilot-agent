from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionLimits:
    max_agent_steps: int
    max_tool_calls: int
    max_llm_calls: int
    max_execution_time_ms: int


def validate_limits(limits: ExecutionLimits) -> None:
    if limits.max_agent_steps <= 0:
        raise ValueError("max_agent_steps must be positive")
    if limits.max_tool_calls <= 0:
        raise ValueError("max_tool_calls must be positive")
    if limits.max_llm_calls <= 0:
        raise ValueError("max_llm_calls must be positive")
    if limits.max_execution_time_ms <= 0:
        raise ValueError("max_execution_time_ms must be positive")
