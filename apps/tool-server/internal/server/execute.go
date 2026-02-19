package server

import (
	"context"
	"os"
	"time"

	"github.com/ops-copilot/tool-server/internal/k8s"
	"github.com/ops-copilot/tool-server/internal/logging"
	"go.opentelemetry.io/otel/propagation"
)

func requiresNamespace(toolName string) bool {
	switch toolName {
	case "k8s.list_namespaces":
		return false
	default:
		return true
	}
}

func executeTool(req toolRequest) toolResponse {
	ctx := context.Background()
	traceparent, ok := req.Args["__traceparent"].(string)
	if ok && traceparent != "" {
		carrier := propagation.MapCarrier{
			"traceparent": traceparent,
		}
		if tracestate, okState := req.Args["__tracestate"].(string); okState && tracestate != "" {
			carrier["tracestate"] = tracestate
		}
		ctx = propagation.TraceContext{}.Extract(ctx, carrier)
	}
	sessionID, _ := req.Args["__session_id"].(string)
	runID, _ := req.Args["__agent_run_id"].(string)
	ctx = logging.WithRunContext(ctx, sessionID, runID)
	logging.Info(
		ctx,
		"tool execute start",
		"tool_name", req.ToolName,
		"args", req.Args,
		"timeout_ms", req.Timeout,
	)
	delete(req.Args, "__traceparent")
	delete(req.Args, "__tracestate")
	delete(req.Args, "__session_id")
	delete(req.Args, "__agent_run_id")
	handler, ok := toolRegistry[req.ToolName]
	if !ok {
		logging.Error(
			ctx,
			"tool execute error",
			"tool_name", req.ToolName,
			"reason", "tool_not_implemented",
			"result_status", "error",
		)
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
	if requiresNamespace(req.ToolName) && namespace == "" {
		logging.Error(
			ctx,
			"tool execute error",
			"tool_name", req.ToolName,
			"reason", "namespace_required",
			"result_status", "error",
		)
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
	if requiresNamespace(req.ToolName) && !k8s.IsAllowed(allowed, namespace) {
		logging.Error(
			ctx,
			"tool execute error",
			"tool_name", req.ToolName,
			"reason", "namespace_not_allowed",
			"namespace", namespace,
			"result_status", "error",
		)
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
		logging.Error(
			ctx,
			"tool execute error",
			"tool_name", req.ToolName,
			"reason", "client_init_failed",
			"error", err.Error(),
			"result_status", "error",
		)
		return toolResponse{
			ToolName:  req.ToolName,
			Status:    "error",
			LatencyMS: 0,
			Truncated: false,
			Result:    nil,
			Error:     MapError(req.ToolName, "execution_error", "client init failed"),
		}
	}
	ctx, endSpan := startToolSpan(ctx, req.ToolName)
	ctx, cancel := context.WithTimeout(ctx, time.Duration(req.Timeout)*time.Millisecond)
	defer cancel()
	result, toolErr := handler(ctx, client, req.Args)
	if toolErr != nil {
		endSpan(map[string]any{
			"namespace":     namespace,
			"session_id":    sessionID,
			"agent_run_id":  runID,
			"result_status": "error",
		})
		logging.Error(
			ctx,
			"tool execute error",
			"tool_name", req.ToolName,
			"namespace", namespace,
			"error", toolErr.Message,
			"result_status", "error",
		)
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
		"session_id":    sessionID,
		"agent_run_id":  runID,
		"result_status": "success",
		"truncated":     didTruncate,
	})
	logging.Info(
		ctx,
		"tool execute success",
		"tool_name", req.ToolName,
		"namespace", namespace,
		"truncated", didTruncate,
		"result_status", "success",
	)
	return toolResponse{
		ToolName:  req.ToolName,
		Status:    "success",
		LatencyMS: 0,
		Truncated: didTruncate,
		Result:    truncated,
		Error:     nil,
	}
}
