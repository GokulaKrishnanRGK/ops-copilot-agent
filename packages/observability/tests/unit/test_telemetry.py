import pytest

from opscopilot_observability.telemetry import _validated_otlp_endpoint


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
