package tests

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/ops-copilot/tool-server/internal/server"
)

func TestHealth(t *testing.T) {
	mux := http.NewServeMux()
	server.RegisterRoutes(mux)
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	resp := httptest.NewRecorder()
	mux.ServeHTTP(resp, req)
	if resp.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.Code)
	}
}
