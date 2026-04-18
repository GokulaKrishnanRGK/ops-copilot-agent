from __future__ import annotations

import os
from dataclasses import dataclass
from importlib import import_module
from typing import Any, Protocol
from urllib.parse import urlparse

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter, SpanExportResult

_configured = False


class MetricNames:
    GEN_AI_CLIENT_TOKEN_USAGE = "gen_ai.client.token.usage"
    GEN_AI_CLIENT_OPERATION_DURATION = "gen_ai.client.operation.duration"
    GEN_AI_CLIENT_REQUESTS = "gen_ai.client.requests"
    GEN_AI_SERVER_TIME_TO_FIRST_TOKEN = "gen_ai.server.time_to_first_token"
    GEN_AI_USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
    GEN_AI_USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
    GEN_AI_REQUEST_MODEL = "gen_ai.request.model"


class LangfuseAdapter(Protocol):
    def score_current_trace(
        self,
        *,
        name: str,
        value: float,
        comment: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        ...

    def create_score(
        self,
        *,
        name: str,
        value: float,
        trace_id: str | None = None,
        session_id: str | None = None,
        comment: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        ...

    def propagate_attributes(
        self,
        *,
        session_id: str | None = None,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> None:
        ...

    def flush(self) -> None:
        ...


@dataclass(frozen=True)
class NoOpLangfuseAdapter:
    def score_current_trace(
        self,
        *,
        name: str,
        value: float,
        comment: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        return None

    def create_score(
        self,
        *,
        name: str,
        value: float,
        trace_id: str | None = None,
        session_id: str | None = None,
        comment: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        return None

    def propagate_attributes(
        self,
        *,
        session_id: str | None = None,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> None:
        return None

    def flush(self) -> None:
        return None


@dataclass(frozen=True)
class HttpLangfuseAdapter:
    client: Any

    def score_current_trace(
        self,
        *,
        name: str,
        value: float,
        comment: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.client.score_current_trace(
            name=name,
            value=value,
            comment=comment,
            metadata=metadata,
        )

    def propagate_attributes(
        self,
        *,
        session_id: str | None = None,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> None:
        self.client.propagate_attributes(
            session_id=session_id,
            user_id=user_id,
            metadata=metadata,
            tags=tags,
        )

    def create_score(
        self,
        *,
        name: str,
        value: float,
        trace_id: str | None = None,
        session_id: str | None = None,
        comment: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.client.create_score(
            name=name,
            value=value,
            trace_id=trace_id,
            session_id=session_id,
            comment=comment,
            metadata=metadata,
            data_type="NUMERIC",
        )

    def flush(self) -> None:
        self.client.flush()


def _validated_otlp_endpoint(raw_endpoint: str) -> str:
    parsed = urlparse(raw_endpoint)
    if parsed.scheme not in {"http", "https"}:
        raise RuntimeError("OTEL_EXPORTER_OTLP_ENDPOINT must start with http:// or https://")
    if not parsed.netloc:
        raise RuntimeError("OTEL_EXPORTER_OTLP_ENDPOINT must include host and port")
    if parsed.path not in {"", "/"}:
        raise RuntimeError(
            "OTEL_EXPORTER_OTLP_ENDPOINT must be the OTLP base URL only (no path), "
            "for example http://localhost:4318"
        )
    if parsed.query or parsed.params or parsed.fragment:
        raise RuntimeError("OTEL_EXPORTER_OTLP_ENDPOINT must not include query, params, or fragment")
    return raw_endpoint.rstrip("/")


def _instrument_provider(module_name: str, class_name: str) -> None:
    try:
        module = import_module(module_name)
        instrumentor = getattr(module, class_name)
        instrumentor().instrument()
    except Exception:
        return


def _instrument_openllmetry() -> None:
    _instrument_provider("opentelemetry.instrumentation.bedrock", "BedrockInstrumentor")


class _LangfuseFilteringExporter(SpanExporter):
    _INCLUDED = frozenset({"chat.run", "chat.run_stream", "tool.call", "rag.retriever", "rag.embed", "rag.retrieve", "get-langfuse-prompt"})
    _INCLUDED_PREFIXES = ("llm.node.", "agent.node.")

    def __init__(self, wrapped: SpanExporter) -> None:
        self._wrapped = wrapped

    def _should_export(self, span) -> bool:
        name = span.name
        return name in self._INCLUDED or any(name.startswith(p) for p in self._INCLUDED_PREFIXES)

    def export(self, spans):
        filtered = [s for s in spans if self._should_export(s)]
        if not filtered:
            return SpanExportResult.SUCCESS
        return self._wrapped.export(filtered)

    def shutdown(self):
        return self._wrapped.shutdown()

    def force_flush(self, timeout_millis: int = 30000):
        return self._wrapped.force_flush(timeout_millis)


def _add_langfuse_span_processor(tracer_provider: TracerProvider) -> None:
    import base64

    langfuse_host = os.getenv("LANGFUSE_HOST")
    langfuse_public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    if not (langfuse_host and langfuse_public_key and langfuse_secret_key):
        return
    langfuse_endpoint = f"{langfuse_host.rstrip('/')}/api/public/otel/v1/traces"
    credentials = base64.b64encode(
        f"{langfuse_public_key}:{langfuse_secret_key}".encode()
    ).decode()
    langfuse_exporter = _LangfuseFilteringExporter(
        OTLPSpanExporter(
            endpoint=langfuse_endpoint,
            headers={"Authorization": f"Basic {credentials}"},
        )
    )
    tracer_provider.add_span_processor(BatchSpanProcessor(langfuse_exporter))


def configure_telemetry(service_name: str) -> None:
    global _configured
    if _configured:
        return

    if isinstance(trace.get_tracer_provider(), TracerProvider):
        _instrument_openllmetry()
        _configured = True
        return

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        _configured = True
        return
    endpoint = _validated_otlp_endpoint(endpoint)

    resolved_service_name = os.getenv("OTEL_SERVICE_NAME", service_name)
    resource = Resource.create({"service.name": resolved_service_name})

    tracer_provider = TracerProvider(resource=resource)
    trace_exporter = OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces")
    tracer_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    _add_langfuse_span_processor(tracer_provider)
    trace.set_tracer_provider(tracer_provider)

    metric_exporter = OTLPMetricExporter(endpoint=f"{endpoint.rstrip('/')}/v1/metrics")
    metric_reader = PeriodicExportingMetricReader(metric_exporter)
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    _instrument_openllmetry()
    _configured = True


def configure_langfuse(
    public_key: str | None = None,
    secret_key: str | None = None,
    host: str | None = None,
) -> LangfuseAdapter:
    resolved_host = host or os.getenv("LANGFUSE_HOST")
    if not resolved_host:
        return NoOpLangfuseAdapter()

    resolved_public_key = public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
    resolved_secret_key = secret_key or os.getenv("LANGFUSE_SECRET_KEY")
    if not resolved_public_key or not resolved_secret_key:
        return NoOpLangfuseAdapter()

    module = import_module("langfuse")
    client_class = getattr(module, "Langfuse")
    client = client_class(
        public_key=resolved_public_key,
        secret_key=resolved_secret_key,
        host=resolved_host,
    )
    return HttpLangfuseAdapter(client=client)
