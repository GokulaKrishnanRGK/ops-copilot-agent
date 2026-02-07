package tests

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/ops-copilot/tool-server/internal/server"
	"github.com/stretchr/testify/require"
)

func TestHealth(t *testing.T) {
	require := require.New(t)
	mux := http.NewServeMux()
	server.RegisterRoutes(mux)
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	resp := httptest.NewRecorder()
	mux.ServeHTTP(resp, req)
	require.Equal(http.StatusOK, resp.Code)
}
