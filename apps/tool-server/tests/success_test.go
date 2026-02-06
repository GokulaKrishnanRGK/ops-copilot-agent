package tests

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"

	"github.com/ops-copilot/tool-server/internal/server"
)

type toolResponse struct {
	Status string         `json:"status"`
	Result map[string]any `json:"result"`
}

func TestListPodsSuccessLocal(t *testing.T) {
	if !hasLocalKubeconfig() {
		t.Skip("kubeconfig not available")
	}
	mux := http.NewServeMux()
	server.RegisterRoutes(mux)
	t.Setenv("K8S_ALLOWED_NAMESPACES", "default")
	body := bytes.NewBufferString("{\"tool_name\":\"k8s.list_pods\",\"args\":{\"namespace\":\"default\"},\"timeout_ms\":3000}")
	req := httptest.NewRequest(http.MethodPost, "/tools/execute", body)
	resp := httptest.NewRecorder()
	mux.ServeHTTP(resp, req)
	if resp.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.Code)
	}
	var payload toolResponse
	if err := json.NewDecoder(resp.Body).Decode(&payload); err != nil {
		t.Fatalf("decode failed")
	}
	if payload.Status != "success" {
		t.Fatalf("expected success")
	}
}

func TestDescribePodSuccessLocal(t *testing.T) {
	if !hasLocalKubeconfig() {
		t.Skip("kubeconfig not available")
	}
	mux := http.NewServeMux()
	server.RegisterRoutes(mux)
	t.Setenv("K8S_ALLOWED_NAMESPACES", "default")
	podName := firstPodName(mux, t)
	if podName == "" {
		t.Skip("no pods found")
	}
	body := bytes.NewBufferString("{\"tool_name\":\"k8s.describe_pod\",\"args\":{\"namespace\":\"default\",\"pod_name\":\"" + podName + "\"},\"timeout_ms\":3000}")
	req := httptest.NewRequest(http.MethodPost, "/tools/execute", body)
	resp := httptest.NewRecorder()
	mux.ServeHTTP(resp, req)
	if resp.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.Code)
	}
}

func firstPodName(mux *http.ServeMux, t *testing.T) string {
	body := bytes.NewBufferString("{\"tool_name\":\"k8s.list_pods\",\"args\":{\"namespace\":\"default\"},\"timeout_ms\":3000}")
	req := httptest.NewRequest(http.MethodPost, "/tools/execute", body)
	resp := httptest.NewRecorder()
	mux.ServeHTTP(resp, req)
	if resp.Code != http.StatusOK {
		return ""
	}
	var payload toolResponse
	if err := json.NewDecoder(resp.Body).Decode(&payload); err != nil {
		return ""
	}
	itemsRaw, ok := payload.Result["items"].([]any)
	if !ok || len(itemsRaw) == 0 {
		return ""
	}
	first, ok := itemsRaw[0].(map[string]any)
	if !ok {
		return ""
	}
	name, _ := first["name"].(string)
	return name
}

func hasLocalKubeconfig() bool {
	path := os.Getenv("KUBECONFIG_PATH")
	if path == "" {
		path = os.Getenv("KUBECONFIG")
	}
	if path == "" {
		path = filepath.Join(os.Getenv("HOME"), ".kube", "config")
	}
	_, err := os.Stat(path)
	return err == nil
}
