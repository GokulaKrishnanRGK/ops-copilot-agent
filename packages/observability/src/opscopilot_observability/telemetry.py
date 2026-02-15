from __future__ import annotations

import os

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import NoOpTracerProvider

_configured = False


def configure_telemetry(default_service_name: str = "ops-copilot") -> None:
    global _configured
    if _configured:
        return

    if not isinstance(trace.get_tracer_provider(), NoOpTracerProvider):
        _configured = True
        return

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        _configured = True
        return

    service_name = os.getenv("OTEL_SERVICE_NAME", default_service_name)
    resource = Resource.create({"service.name": service_name})

    tracer_provider = TracerProvider(resource=resource)
    trace_exporter = OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces")
    tracer_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(tracer_provider)

    metric_exporter = OTLPMetricExporter(endpoint=f"{endpoint.rstrip('/')}/v1/metrics")
    metric_reader = PeriodicExportingMetricReader(metric_exporter)
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    _configured = True
