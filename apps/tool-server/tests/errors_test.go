package tests

import (
	"testing"

	"github.com/ops-copilot/tool-server/internal/server"
)

func TestStatusForError(t *testing.T) {
	cases := map[string]int{
		"invalid_input":     400,
		"permission_denied": 403,
		"timeout":           408,
		"not_found":         404,
		"execution_error":   500,
	}
	for errType, expected := range cases {
		err := server.MapError("tool", errType, "msg")
		if server.StatusForError(err) != expected {
			t.Fatalf("expected %d for %s", expected, errType)
		}
	}
}
