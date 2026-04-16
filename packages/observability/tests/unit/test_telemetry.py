import pytest

from opscopilot_observability import telemetry
from opscopilot_observability.telemetry import (
    _instrument_openllmetry,
    _validated_otlp_endpoint,
    configure_telemetry,
)


def test_validated_otlp_endpoint_accepts_http_base() -> None:
    assert _validated_otlp_endpoint("http://localhost:4318") == "http://localhost:4318"


def test_validated_otlp_endpoint_accepts_https_base() -> None:
    assert _validated_otlp_endpoint("https://otel.example.com") == "https://otel.example.com"


def test_validated_otlp_endpoint_rejects_non_http_scheme() -> None:
    with pytest.raises(RuntimeError, match="must start with http:// or https://"):
        _validated_otlp_endpoint("grpc://localhost:4317")


def test_validated_otlp_endpoint_rejects_path() -> None:
    with pytest.raises(RuntimeError, match="base URL only"):
        _validated_otlp_endpoint("http://localhost:4318/v1/traces")


def test_validated_otlp_endpoint_rejects_missing_host() -> None:
    with pytest.raises(RuntimeError, match="must include host and port"):
        _validated_otlp_endpoint("http://")


def test_validated_otlp_endpoint_rejects_query_fragment() -> None:
    with pytest.raises(RuntimeError, match="must not include query"):
        _validated_otlp_endpoint("http://localhost:4318?x=1")


def test_configure_telemetry_requires_service_name() -> None:
    with pytest.raises(TypeError):
        configure_telemetry()


def test_instrument_openllmetry_disables_content_tracing_by_default(monkeypatch) -> None:
    calls = []

    class FakeInstrumentor:
        def instrument(self) -> None:
            calls.append("instrumented")

    class FakeModule:
        BedrockInstrumentor = FakeInstrumentor
        OpenAIInstrumentor = FakeInstrumentor

    def fake_import_module(name: str):
        if name in {
            "opentelemetry.instrumentation.bedrock",
            "opentelemetry.instrumentation.openai_v2",
        }:
            return FakeModule
        raise AssertionError(name)

    monkeypatch.delenv("TRACELOOP_TRACE_CONTENT", raising=False)
    monkeypatch.setattr(telemetry, "import_module", fake_import_module)

    _instrument_openllmetry()

    assert calls == ["instrumented", "instrumented"]
    assert telemetry.os.getenv("TRACELOOP_TRACE_CONTENT") == "false"
