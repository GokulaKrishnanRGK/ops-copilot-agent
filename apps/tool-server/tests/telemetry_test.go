package tests

import (
	"testing"

	"github.com/ops-copilot/tool-server/internal/server"
)

func TestAttributesFromMap(t *testing.T) {
	attrs := map[string]any{
		"tool_name":  "k8s.list_pods",
		"truncated":  true,
		"latency_ms": 10,
		"cost":       1.2,
	}
	kvs := server.AttributesFromMap(attrs)
	if len(kvs) != 4 {
		t.Fatalf("expected 4 attributes, got %d", len(kvs))
	}
}
