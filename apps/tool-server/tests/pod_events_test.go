package tests

import (
	"bytes"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/ops-copilot/tool-server/internal/server"
)

func TestGetPodEventsDeniedNamespace(t *testing.T) {
	mux := http.NewServeMux()
	server.RegisterRoutes(mux)
	t.Setenv("K8S_ALLOWED_NAMESPACES", "default")
	body := bytes.NewBufferString("{\"tool_name\":\"k8s.get_pod_events\",\"args\":{\"namespace\":\"kube-system\",\"pod_name\":\"p1\"},\"timeout_ms\":1000}")
	req := httptest.NewRequest(http.MethodPost, "/tools/execute", body)
	resp := httptest.NewRecorder()
	mux.ServeHTTP(resp, req)
	if resp.Code != http.StatusForbidden {
		t.Fatalf("expected 403, got %d", resp.Code)
	}
}
