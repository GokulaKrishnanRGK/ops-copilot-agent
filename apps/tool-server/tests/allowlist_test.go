package tests

import (
	"testing"

	"github.com/ops-copilot/tool-server/internal/k8s"
	"github.com/stretchr/testify/require"
)

func TestParseAllowlist(t *testing.T) {
	require := require.New(t)
	allowed := k8s.ParseAllowlist("default, kube-system ,dev")
	require.Len(allowed, 3)
	require.True(k8s.IsAllowed(allowed, "default"))
}

func TestAllowlistEmpty(t *testing.T) {
	require := require.New(t)
	allowed := k8s.ParseAllowlist("")
	require.False(k8s.IsAllowed(allowed, "default"))
}
