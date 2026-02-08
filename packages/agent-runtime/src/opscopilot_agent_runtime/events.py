from dataclasses import dataclass


@dataclass(frozen=True)
class AgentEvent:
    event_type: str
    payload: dict


def emit_event(event: AgentEvent) -> dict:
    return {"event": event}
