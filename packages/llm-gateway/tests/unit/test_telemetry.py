from opscopilot_llm_gateway.telemetry import build_span_attributes


def test_build_span_attributes_uses_genai_conventions():
    attrs = build_span_attributes(
        model_id="m1",
        agent_node="planner",
        tokens_input=1,
        tokens_output=2,
        cost_usd=0.01,
        session_id="s1",
        agent_run_id="r1",
    )
    assert attrs["gen_ai.request.model"] == "m1"
    assert attrs["gen_ai.usage.input_tokens"] == 1
    assert attrs["gen_ai.usage.output_tokens"] == 2
    assert attrs["agent_node"] == "planner"
    assert attrs["cost_usd"] == 0.01
    assert attrs["session_id"] == "s1"
    assert attrs["agent_run_id"] == "r1"
    assert "model_id" not in attrs
    assert "tokens_input" not in attrs
    assert "tokens_output" not in attrs
