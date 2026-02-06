package tests

import (
	"testing"

	"github.com/ops-copilot/tool-server/internal/k8s"
)

func TestParseAllowlist(t *testing.T) {
	allowed := k8s.ParseAllowlist("default, kube-system ,dev")
	if len(allowed) != 3 {
		t.Fatalf("expected 3, got %d", len(allowed))
	}
	if !k8s.IsAllowed(allowed, "default") {
		t.Fatalf("default should be allowed")
	}
}

func TestAllowlistEmpty(t *testing.T) {
	allowed := k8s.ParseAllowlist("")
	if k8s.IsAllowed(allowed, "default") {
		t.Fatalf("empty allowlist should deny")
	}
}
