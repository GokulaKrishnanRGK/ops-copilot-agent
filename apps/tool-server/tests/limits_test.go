package tests

import (
	"testing"

	"github.com/ops-copilot/tool-server/internal/server"
)

func TestRedactStrings(t *testing.T) {
	input := map[string]any{
		"token":  "abc",
		"nested": map[string]any{"password": "secret", "ok": "v"},
	}
	redacted := server.RedactStrings(input).(map[string]any)
	if redacted["token"].(string) != "[REDACTED]" {
		t.Fatalf("token not redacted")
	}
	nested := redacted["nested"].(map[string]any)
	if nested["password"].(string) != "[REDACTED]" {
		t.Fatalf("password not redacted")
	}
	if nested["ok"].(string) != "v" {
		t.Fatalf("value changed")
	}
}

func TestTruncateJSON(t *testing.T) {
	payload := map[string]any{"a": "b"}
	truncated, did := server.TruncateJSON(payload, 5)
	if !did {
		t.Fatalf("expected truncation")
	}
	result := truncated.(map[string]any)
	if result["truncated"].(bool) != true {
		t.Fatalf("truncated flag missing")
	}
}
