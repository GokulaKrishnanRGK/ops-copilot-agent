from opscopilot_llm_gateway.telemetry import build_span_attributes


def test_build_span_attributes():
    attrs = build_span_attributes(
        model_id="m1",
        agent_node="planner",
        tokens_input=1,
        tokens_output=2,
        cost_usd=0.01,
        session_id="s1",
        agent_run_id="r1",
    )
    assert attrs["model_id"] == "m1"
    assert attrs["agent_node"] == "planner"
    assert attrs["tokens_input"] == 1
    assert attrs["tokens_output"] == 2
    assert attrs["cost_usd"] == 0.01
    assert attrs["session_id"] == "s1"
    assert attrs["agent_run_id"] == "r1"
