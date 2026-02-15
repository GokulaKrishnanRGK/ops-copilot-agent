package server

import (
	"context"
	"os"
	"time"

	"github.com/ops-copilot/tool-server/internal/k8s"
	"go.opentelemetry.io/otel/propagation"
)

func executeTool(req toolRequest) toolResponse {
	debugLogf("tool execute start name=%s args=%v timeout_ms=%d", req.ToolName, req.Args, req.Timeout)
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
	delete(req.Args, "__traceparent")
	delete(req.Args, "__tracestate")
	delete(req.Args, "__session_id")
	delete(req.Args, "__agent_run_id")
	handler, ok := toolRegistry[req.ToolName]
	if !ok {
		debugLogf("tool execute error name=%s reason=tool_not_implemented", req.ToolName)
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
		debugLogf("tool execute error name=%s reason=namespace_required", req.ToolName)
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
		debugLogf("tool execute error name=%s reason=namespace_not_allowed namespace=%s", req.ToolName, namespace)
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
		debugLogf("tool execute error name=%s reason=client_init_failed err=%v", req.ToolName, err)
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
		debugLogf("tool execute error name=%s namespace=%s err=%v", req.ToolName, namespace, toolErr)
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
	debugLogf("tool execute success name=%s namespace=%s truncated=%t", req.ToolName, namespace, didTruncate)
	return toolResponse{
		ToolName:  req.ToolName,
		Status:    "success",
		LatencyMS: 0,
		Truncated: didTruncate,
		Result:    truncated,
		Error:     nil,
	}
}
