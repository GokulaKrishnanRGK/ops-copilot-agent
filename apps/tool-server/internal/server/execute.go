package server

import (
	"context"
	"encoding/json"
	"net/http"
	"os"
	"time"

	"github.com/ops-copilot/tool-server/internal/k8s"
)

func toolExecuteHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	decoder := json.NewDecoder(r.Body)
	var req toolRequest
	if err := decoder.Decode(&req); err != nil {
		w.WriteHeader(http.StatusBadRequest)
		_ = json.NewEncoder(w).Encode(toolResponse{
			ToolName:  "",
			Status:    "error",
			LatencyMS: 0,
			Truncated: false,
			Result:    nil,
			Error:     MapError("", "invalid_input", "invalid json"),
		})
		return
	}
	start := time.Now()
	resp := executeTool(req)
	resp.LatencyMS = int(time.Since(start).Milliseconds())
	w.WriteHeader(statusForResponse(resp))
	_ = json.NewEncoder(w).Encode(resp)
}

func executeTool(req toolRequest) toolResponse {
	handler, ok := toolRegistry[req.ToolName]
	if !ok {
		return toolResponse{
			ToolName:  req.ToolName,
			Status:    "error",
			LatencyMS: 0,
			Truncated: false,
			Result:    nil,
			Error:     MapError(req.ToolName, "execution_error", "tool not implemented"),
		}
	}
	namespace, _ := req.Args["namespace"].(string)
	if namespace == "" {
		return toolResponse{
			ToolName:  req.ToolName,
			Status:    "error",
			LatencyMS: 0,
			Truncated: false,
			Result:    nil,
			Error:     MapError(req.ToolName, "invalid_input", "namespace required"),
		}
	}
	allowed := k8s.ParseAllowlist(os.Getenv("K8S_ALLOWED_NAMESPACES"))
	if !k8s.IsAllowed(allowed, namespace) {
		return toolResponse{
			ToolName:  req.ToolName,
			Status:    "error",
			LatencyMS: 0,
			Truncated: false,
			Result:    nil,
			Error:     MapError(req.ToolName, "permission_denied", "namespace not allowed"),
		}
	}
	client, err := k8s.NewClient()
	if err != nil {
		return toolResponse{
			ToolName:  req.ToolName,
			Status:    "error",
			LatencyMS: 0,
			Truncated: false,
			Result:    nil,
			Error:     MapError(req.ToolName, "execution_error", "client init failed"),
		}
	}
	ctx, endSpan := startToolSpan(context.Background(), req.ToolName)
	ctx, cancel := context.WithTimeout(ctx, time.Duration(req.Timeout)*time.Millisecond)
	defer cancel()
	result, toolErr := handler(ctx, client, req.Args)
	if toolErr != nil {
		endSpan(map[string]any{
			"namespace":     namespace,
			"result_status": "error",
		})
		return toolResponse{
			ToolName:  req.ToolName,
			Status:    "error",
			LatencyMS: 0,
			Truncated: false,
			Result:    nil,
			Error:     toolErr,
		}
	}
	redacted := RedactStrings(result)
	truncated, didTruncate := TruncateJSON(redacted, MaxOutputBytes())
	endSpan(map[string]any{
		"namespace":     namespace,
		"result_status": "success",
		"truncated":     didTruncate,
	})
	return toolResponse{
		ToolName:  req.ToolName,
		Status:    "success",
		LatencyMS: 0,
		Truncated: didTruncate,
		Result:    truncated,
		Error:     nil,
	}
}

func statusForResponse(resp toolResponse) int {
	if resp.Status == "success" {
		return http.StatusOK
	}
	return StatusForError(resp.Error)
}
