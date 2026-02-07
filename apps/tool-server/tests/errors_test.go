package tests

import (
	"testing"

	"github.com/ops-copilot/tool-server/internal/server"
	"github.com/stretchr/testify/require"
)

func TestStatusForError(t *testing.T) {
	require := require.New(t)
	cases := map[string]int{
		"invalid_input":     400,
		"permission_denied": 403,
		"timeout":           408,
		"not_found":         404,
		"execution_error":   500,
	}
	for errType, expected := range cases {
		err := server.MapError("tool", errType, "msg")
		require.Equal(expected, server.StatusForError(err))
	}
}
