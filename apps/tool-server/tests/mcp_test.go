package tests

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"

	"github.com/ops-copilot/tool-server/internal/server"
	"github.com/stretchr/testify/require"
)

type jsonrpcResponse struct {
	Result map[string]any `json:"result"`
	Error  map[string]any `json:"error"`
}

type toolResponse struct {
	ToolName string         `json:"tool_name"`
	Status   string         `json:"status"`
	Result   map[string]any `json:"result"`
}

func TestMCPToolsList(t *testing.T) {
	require := require.New(t)
	t.Setenv("MCP_JSON_RESPONSE", "true")
	mux := http.NewServeMux()
	server.RegisterRoutes(mux)
	ts := httptest.NewServer(mux)
	defer ts.Close()

	require.NoError(mcpInitialize(ts.URL))

	toolsList := map[string]any{
		"jsonrpc": "2.0",
		"id":      2,
		"method":  "tools/list",
		"params":  map[string]any{},
	}
	listBody, _ := json.Marshal(toolsList)
	listReq, _ := http.NewRequest(http.MethodPost, ts.URL+"/mcp", bytes.NewBuffer(listBody))
	listReq.Header.Set("Content-Type", "application/json")
	listReq.Header.Set("Accept", "application/json, text/event-stream")
	listResp, err := http.DefaultClient.Do(listReq)
	require.NoError(err)
	require.Equal(http.StatusOK, listResp.StatusCode)
	defer listResp.Body.Close()

	var decoded jsonrpcResponse
	require.NoError(json.NewDecoder(listResp.Body).Decode(&decoded))
	toolsRaw, ok := decoded.Result["tools"].([]any)
	require.True(ok)
	found := false
	foundNamespaces := false
	for _, item := range toolsRaw {
		tool, ok := item.(map[string]any)
		if !ok {
			continue
		}
		if tool["name"] == "k8s.list_pods" {
			found = true
		}
		if tool["name"] == "k8s.list_namespaces" {
			foundNamespaces = true
		}
	}
	require.True(found)
	require.True(foundNamespaces)
}

func TestMCPListPods(t *testing.T) {
	require := require.New(t)
	if !hasLocalKubeconfig() {
		t.Skip("kubeconfig not available")
	}
	t.Setenv("MCP_JSON_RESPONSE", "true")
	t.Setenv("K8S_ALLOWED_NAMESPACES", "default")
	mux := http.NewServeMux()
	server.RegisterRoutes(mux)
	ts := httptest.NewServer(mux)
	defer ts.Close()

	require.NoError(mcpInitialize(ts.URL))

	call := map[string]any{
		"jsonrpc": "2.0",
		"id":      3,
		"method":  "tools/call",
		"params": map[string]any{
			"name": "k8s.list_pods",
			"arguments": map[string]any{
				"namespace":      "default",
				"label_selector": "",
			},
		},
	}
	callBody, _ := json.Marshal(call)
	callReq, _ := http.NewRequest(http.MethodPost, ts.URL+"/mcp", bytes.NewBuffer(callBody))
	callReq.Header.Set("Content-Type", "application/json")
	callReq.Header.Set("Accept", "application/json, text/event-stream")
	callResp, err := http.DefaultClient.Do(callReq)
	require.NoError(err)
	require.Equal(http.StatusOK, callResp.StatusCode)
	raw := readBody(callResp.Body)
	t.Logf("raw response: %s", string(raw))
	var decoded jsonrpcResponse
	require.NoError(json.Unmarshal(raw, &decoded))
	contentRaw, ok := decoded.Result["content"].([]any)
	require.True(ok)
	require.NotEmpty(contentRaw)
	first, ok := contentRaw[0].(map[string]any)
	require.True(ok)
	text, ok := first["text"].(string)
	require.True(ok)
	var toolResp toolResponse
	require.NoError(json.Unmarshal([]byte(text), &toolResp))
	items, ok := toolResp.Result["items"].([]any)
	require.True(ok)
	t.Logf("pods: %v", items)
	require.NotEmpty(items)
}

func TestMCPDescribePod(t *testing.T) {
	require := require.New(t)
	if !hasLocalKubeconfig() {
		t.Skip("kubeconfig not available")
	}
	t.Setenv("MCP_JSON_RESPONSE", "true")
	t.Setenv("K8S_ALLOWED_NAMESPACES", "default")
	mux := http.NewServeMux()
	server.RegisterRoutes(mux)
	ts := httptest.NewServer(mux)
	defer ts.Close()

	require.NoError(mcpInitialize(ts.URL))
	podName := firstPodName(ts.URL)
	if podName == "" {
		t.Skip("no pods found")
	}

	call := map[string]any{
		"jsonrpc": "2.0",
		"id":      4,
		"method":  "tools/call",
		"params": map[string]any{
			"name": "k8s.describe_pod",
			"arguments": map[string]any{
				"namespace": "default",
				"pod_name":  podName,
			},
		},
	}
	callBody, _ := json.Marshal(call)
	callReq, _ := http.NewRequest(http.MethodPost, ts.URL+"/mcp", bytes.NewBuffer(callBody))
	callReq.Header.Set("Content-Type", "application/json")
	callReq.Header.Set("Accept", "application/json, text/event-stream")
	callResp, err := http.DefaultClient.Do(callReq)
	require.NoError(err)
	require.Equal(http.StatusOK, callResp.StatusCode)
	raw := readBody(callResp.Body)
	t.Logf("raw response: %s", string(raw))
	var decoded jsonrpcResponse
	require.NoError(json.Unmarshal(raw, &decoded))
	contentRaw, ok := decoded.Result["content"].([]any)
	require.True(ok)
	require.NotEmpty(contentRaw)
}

func mcpInitialize(baseURL string) error {
	initialize := map[string]any{
		"jsonrpc": "2.0",
		"id":      1,
		"method":  "initialize",
		"params": map[string]any{
			"protocolVersion": "2024-11-05",
			"capabilities": map[string]any{
				"tools": map[string]any{},
			},
			"clientInfo": map[string]any{
				"name":    "test-client",
				"version": "0.0.0",
			},
		},
	}
	initBody, _ := json.Marshal(initialize)
	initReq, _ := http.NewRequest(http.MethodPost, baseURL+"/mcp", bytes.NewBuffer(initBody))
	initReq.Header.Set("Content-Type", "application/json")
	initReq.Header.Set("Accept", "application/json, text/event-stream")
	initResp, err := http.DefaultClient.Do(initReq)
	if err != nil {
		return err
	}
	if initResp.StatusCode != http.StatusOK {
		return errStatus(initResp.StatusCode)
	}
	return nil
}

func firstPodName(baseURL string) string {
	call := map[string]any{
		"jsonrpc": "2.0",
		"id":      5,
		"method":  "tools/call",
		"params": map[string]any{
			"name": "k8s.list_pods",
			"arguments": map[string]any{
				"namespace":      "default",
				"label_selector": "",
			},
		},
	}
	callBody, _ := json.Marshal(call)
	callReq, _ := http.NewRequest(http.MethodPost, baseURL+"/mcp", bytes.NewBuffer(callBody))
	callReq.Header.Set("Content-Type", "application/json")
	callReq.Header.Set("Accept", "application/json, text/event-stream")
	callResp, err := http.DefaultClient.Do(callReq)
	if err != nil {
		return ""
	}
	if callResp.StatusCode != http.StatusOK {
		return ""
	}
	defer callResp.Body.Close()

	var decoded jsonrpcResponse
	body := readBody(callResp.Body)
	if err := json.Unmarshal(body, &decoded); err != nil {
		return ""
	}
	contentRaw, ok := decoded.Result["content"].([]any)
	if !ok || len(contentRaw) == 0 {
		return ""
	}
	first, ok := contentRaw[0].(map[string]any)
	if !ok {
		return ""
	}
	text, ok := first["text"].(string)
	if !ok {
		return ""
	}
	var toolResp toolResponse
	if err := json.Unmarshal([]byte(text), &toolResp); err != nil {
		return ""
	}
	items, ok := toolResp.Result["items"].([]any)
	if !ok || len(items) == 0 {
		return ""
	}
	item, ok := items[0].(map[string]any)
	if !ok {
		return ""
	}
	name, _ := item["name"].(string)
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

func errStatus(code int) error {
	return &statusError{code: code}
}

type statusError struct {
	code int
}

func (e *statusError) Error() string {
	return "unexpected status"
}

func readBody(body io.ReadCloser) []byte {
	defer body.Close()
	data, _ := io.ReadAll(body)
	return data
}
