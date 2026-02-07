package tests

import (
	"testing"

	"github.com/ops-copilot/tool-server/internal/server"
	"github.com/stretchr/testify/require"
)

func TestRedactStrings(t *testing.T) {
	require := require.New(t)
	input := map[string]any{
		"token":  "abc",
		"nested": map[string]any{"password": "secret", "ok": "v"},
	}
	redacted := server.RedactStrings(input).(map[string]any)
	require.Equal("[REDACTED]", redacted["token"].(string))
	nested := redacted["nested"].(map[string]any)
	require.Equal("[REDACTED]", nested["password"].(string))
	require.Equal("v", nested["ok"].(string))
}

func TestTruncateJSON(t *testing.T) {
	require := require.New(t)
	payload := map[string]any{"a": "b"}
	truncated, did := server.TruncateJSON(payload, 5)
	require.True(did)
	result := truncated.(map[string]any)
	require.True(result["truncated"].(bool))
}
