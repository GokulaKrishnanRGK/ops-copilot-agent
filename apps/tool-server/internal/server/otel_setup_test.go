package server

import (
	"context"
	"os"
	"testing"
)

func TestValidatedOTLPEndpointEmptyDisabled(t *testing.T) {
	endpoint, enabled, err := validatedOTLPEndpoint("")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if enabled {
		t.Fatalf("expected disabled")
	}
	if endpoint != "" {
		t.Fatalf("unexpected endpoint %q", endpoint)
	}
}

func TestValidatedOTLPEndpointAcceptsBaseURL(t *testing.T) {
	endpoint, enabled, err := validatedOTLPEndpoint("http://localhost:4318")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !enabled {
		t.Fatalf("expected enabled")
	}
	if endpoint != "http://localhost:4318" {
		t.Fatalf("unexpected endpoint %q", endpoint)
	}
}

func TestValidatedOTLPEndpointRejectsPath(t *testing.T) {
	_, _, err := validatedOTLPEndpoint("http://localhost:4318/v1/traces")
	if err == nil {
		t.Fatal("expected error")
	}
}

func TestSetupTelemetryNoEndpointIsNoop(t *testing.T) {
	t.Setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
	shutdown, err := SetupTelemetry(context.Background())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if shutdown == nil {
		t.Fatal("expected shutdown function")
	}
	if err := shutdown(context.Background()); err != nil {
		t.Fatalf("unexpected shutdown error: %v", err)
	}
}

func TestSetupTelemetryInvalidEndpointFailsFast(t *testing.T) {
	t.Setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "grpc://localhost:4317")
	shutdown, err := SetupTelemetry(context.Background())
	if err == nil {
		t.Fatal("expected error")
	}
	if shutdown != nil {
		t.Fatal("expected nil shutdown on setup failure")
	}
}

func TestSetupTelemetryWithEndpointReturnsShutdown(t *testing.T) {
	t.Setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
	t.Setenv("OTEL_SERVICE_NAME", "tool-server-test")
	shutdown, err := SetupTelemetry(context.Background())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if shutdown == nil {
		t.Fatal("expected shutdown function")
	}
	if err := shutdown(context.Background()); err != nil {
		t.Fatalf("unexpected shutdown error: %v", err)
	}
}

func TestMain(m *testing.M) {
	// Ensure no ambient value from shell affects endpoint validation tests.
	_ = os.Unsetenv("OTEL_EXPORTER_OTLP_ENDPOINT")
	os.Exit(m.Run())
}
