import pytest

from opscopilot_observability import telemetry
from opscopilot_observability.telemetry import (
    HttpLangfuseAdapter,
    MetricNames,
    NoOpLangfuseAdapter,
    configure_langfuse,
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


def test_metric_names_use_genai_conventions() -> None:
    assert MetricNames.GEN_AI_CLIENT_TOKEN_USAGE == "gen_ai.client.token.usage"
    assert MetricNames.GEN_AI_CLIENT_OPERATION_DURATION == "gen_ai.client.operation.duration"
    assert MetricNames.GEN_AI_USAGE_INPUT_TOKENS == "gen_ai.usage.input_tokens"
    assert MetricNames.GEN_AI_USAGE_OUTPUT_TOKENS == "gen_ai.usage.output_tokens"
    assert MetricNames.GEN_AI_REQUEST_MODEL == "gen_ai.request.model"


def test_configure_langfuse_returns_noop_without_host(monkeypatch) -> None:
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

    adapter = configure_langfuse()

    assert isinstance(adapter, NoOpLangfuseAdapter)


def test_configure_langfuse_returns_noop_without_keys(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_HOST", "http://localhost:3001")
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

    adapter = configure_langfuse()

    assert isinstance(adapter, NoOpLangfuseAdapter)


def test_configure_langfuse_returns_http_adapter(monkeypatch) -> None:
    created = {}

    class FakeClient:
        def __init__(self, **kwargs):
            created.update(kwargs)

        def score_current_trace(self, **kwargs) -> None:
            created["score"] = kwargs

        def propagate_attributes(self, **kwargs) -> None:
            created["attributes"] = kwargs

        def flush(self) -> None:
            created["flushed"] = True

    class FakeModule:
        Langfuse = FakeClient

    def fake_import_module(name: str):
        if name == "langfuse":
            return FakeModule
        raise AssertionError(name)

    monkeypatch.setattr(telemetry, "import_module", fake_import_module)

    adapter = configure_langfuse(
        public_key="pk",
        secret_key="sk",
        host="http://localhost:3001",
    )

    assert isinstance(adapter, HttpLangfuseAdapter)
    assert created["public_key"] == "pk"
    assert created["secret_key"] == "sk"
    assert created["host"] == "http://localhost:3001"

    adapter.score_current_trace(name="quality", value=1.0)
    adapter.propagate_attributes(session_id="s1", tags=["demo"])
    adapter.flush()

    assert created["score"]["name"] == "quality"
    assert created["attributes"]["session_id"] == "s1"
    assert created["flushed"] is True
