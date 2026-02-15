package server

import (
	"context"
	"fmt"
	"net/url"
	"os"
	"strings"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

func SetupTelemetry(ctx context.Context) (func(context.Context) error, error) {
	endpoint, enabled, err := validatedOTLPEndpoint(os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT"))
	if err != nil {
		return nil, err
	}
	if !enabled {
		return func(context.Context) error { return nil }, nil
	}

	parsed, err := url.Parse(endpoint)
	if err != nil {
		return nil, err
	}

	exporterOptions := []otlptracehttp.Option{
		otlptracehttp.WithEndpoint(parsed.Host),
		otlptracehttp.WithURLPath("/v1/traces"),
	}
	if parsed.Scheme == "http" {
		exporterOptions = append(exporterOptions, otlptracehttp.WithInsecure())
	}

	traceExporter, err := otlptracehttp.New(ctx, exporterOptions...)
	if err != nil {
		return nil, fmt.Errorf("initialize OTLP trace exporter: %w", err)
	}

	serviceName := strings.TrimSpace(os.Getenv("OTEL_SERVICE_NAME"))
	if serviceName == "" {
		serviceName = "ops-copilot-tool-server"
	}
	resourceAttrs, err := resource.New(
		ctx,
		resource.WithAttributes(attribute.String("service.name", serviceName)),
	)
	if err != nil {
		return nil, fmt.Errorf("initialize OTEL resource: %w", err)
	}

	traceProvider := sdktrace.NewTracerProvider(
		sdktrace.WithResource(resourceAttrs),
		sdktrace.WithBatcher(traceExporter),
	)
	otel.SetTracerProvider(traceProvider)
	otel.SetTextMapPropagator(propagation.TraceContext{})
	return traceProvider.Shutdown, nil
}

func validatedOTLPEndpoint(raw string) (string, bool, error) {
	value := strings.TrimSpace(raw)
	if value == "" {
		return "", false, nil
	}
	parsed, err := url.Parse(value)
	if err != nil {
		return "", false, fmt.Errorf("invalid OTEL_EXPORTER_OTLP_ENDPOINT: %w", err)
	}
	if parsed.Scheme != "http" && parsed.Scheme != "https" {
		return "", false, fmt.Errorf("OTEL_EXPORTER_OTLP_ENDPOINT must start with http:// or https://")
	}
	if parsed.Host == "" {
		return "", false, fmt.Errorf("OTEL_EXPORTER_OTLP_ENDPOINT must include host and port")
	}
	if parsed.Path != "" && parsed.Path != "/" {
		return "", false, fmt.Errorf("OTEL_EXPORTER_OTLP_ENDPOINT must be base URL only (no path)")
	}
	if parsed.RawQuery != "" || parsed.Fragment != "" {
		return "", false, fmt.Errorf("OTEL_EXPORTER_OTLP_ENDPOINT must not include query or fragment")
	}
	return strings.TrimSuffix(value, "/"), true, nil
}
