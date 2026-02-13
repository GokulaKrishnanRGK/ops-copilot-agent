from opscopilot_api.services.event_mapper import (
    agent_run_completed,
    agent_run_failed,
    agent_run_started,
    assistant_delta,
    error_event,
)


def test_event_mapper_envelope_shape() -> None:
    event = agent_run_started("s1", "r1")
    assert event["type"] == "agent_run.started"
    assert event["session_id"] == "s1"
    assert event["agent_run_id"] == "r1"
    assert "timestamp" in event
    assert event["payload"]["agent_run_id"] == "r1"


def test_event_mapper_payloads() -> None:
    delta = assistant_delta("s1", "r1", "hello")
    assert delta["payload"]["text"] == "hello"
    completed = agent_run_completed("s1", "r1")
    assert completed["payload"]["summary"] == "completed"
    err = error_event("s1", "r1", "runtime_error", "boom")
    assert err["payload"]["error_type"] == "runtime_error"
    failed = agent_run_failed("s1", "r1", "boom", "runtime_error")
    assert failed["payload"]["failure_type"] == "runtime_error"
