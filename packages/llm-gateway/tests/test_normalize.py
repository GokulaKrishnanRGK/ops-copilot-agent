from opscopilot_llm_gateway.normalize import (
    normalize_error,
    normalize_output_json,
    normalize_output_text,
    normalize_response,
)


def test_normalize_output_text():
    output = normalize_output_text("ok")
    assert output.type == "text"
    assert output.text == "ok"
    assert output.json is None


def test_normalize_output_json():
    output = normalize_output_json({"a": 1})
    assert output.type == "json"
    assert output.text is None
    assert output.json == {"a": 1}


def test_normalize_error_valid_type():
    err = normalize_error("timeout", "t")
    assert err.error_type == "timeout"


def test_normalize_error_invalid_type():
    err = normalize_error("nope", "x")
    assert err.error_type == "unknown_error"


def test_normalize_response():
    output = normalize_output_text("ok")
    resp = normalize_response(output, 1, 2, 0.01, 10, {"p": 1}, None)
    assert resp.tokens_input == 1
    assert resp.tokens_output == 2
    assert resp.cost_usd == 0.01
    assert resp.latency_ms == 10
    assert resp.provider_metadata == {"p": 1}
    assert resp.error is None
