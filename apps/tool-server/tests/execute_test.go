package tests

import (
	"bytes"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/ops-copilot/tool-server/internal/server"
)

func TestExecuteToolInvalidPayload(t *testing.T) {
	mux := http.NewServeMux()
	server.RegisterRoutes(mux)
	req := httptest.NewRequest(http.MethodPost, "/tools/execute", bytes.NewBufferString("{"))
	resp := httptest.NewRecorder()
	mux.ServeHTTP(resp, req)
	if resp.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", resp.Code)
	}
}

func TestExecuteToolNotImplemented(t *testing.T) {
	mux := http.NewServeMux()
	server.RegisterRoutes(mux)
	body := bytes.NewBufferString("{\"tool_name\":\"k8s.unknown\",\"args\":{},\"timeout_ms\":1000}")
	req := httptest.NewRequest(http.MethodPost, "/tools/execute", body)
	resp := httptest.NewRecorder()
	mux.ServeHTTP(resp, req)
	if resp.Code != http.StatusInternalServerError {
		t.Fatalf("expected 500, got %d", resp.Code)
	}
}
