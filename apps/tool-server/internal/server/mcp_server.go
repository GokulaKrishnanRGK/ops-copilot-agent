package server

import (
	"context"
	"net/http"
	"os"
	"strconv"

	mcp "github.com/modelcontextprotocol/go-sdk/mcp"
	"github.com/ops-copilot/tool-server/internal/logging"
)

type listPodsInput struct {
	InstrumentationInput
	Namespace     string `json:"namespace"`
	LabelSelector string `json:"label_selector"`
}

type describePodInput struct {
	InstrumentationInput
	Namespace string `json:"namespace"`
	PodName   string `json:"pod_name"`
}

type podEventsInput struct {
	InstrumentationInput
	Namespace string `json:"namespace"`
	PodName   string `json:"pod_name"`
}

type podLogsInput struct {
	InstrumentationInput
	Namespace string `json:"namespace"`
	PodName   string `json:"pod_name"`
	Container string `json:"container"`
	TailLines int    `json:"tail_lines"`
}

type describeDeploymentInput struct {
	InstrumentationInput
	Namespace      string `json:"namespace"`
	DeploymentName string `json:"deployment_name"`
}

type InstrumentationInput struct {
	Traceparent *string `json:"__traceparent,omitempty"`
	Tracestate  *string `json:"__tracestate,omitempty"`
	SessionID   *string `json:"__session_id,omitempty"`
	AgentRunID  *string `json:"__agent_run_id,omitempty"`
}

func addInternalArgs(
	payload map[string]any,
	instrumentation InstrumentationInput,
) {
	if instrumentation.Traceparent != nil && *instrumentation.Traceparent != "" {
		payload["__traceparent"] = *instrumentation.Traceparent
	}
	if instrumentation.Tracestate != nil && *instrumentation.Tracestate != "" {
		payload["__tracestate"] = *instrumentation.Tracestate
	}
	if instrumentation.SessionID != nil && *instrumentation.SessionID != "" {
		payload["__session_id"] = *instrumentation.SessionID
	}
	if instrumentation.AgentRunID != nil && *instrumentation.AgentRunID != "" {
		payload["__agent_run_id"] = *instrumentation.AgentRunID
	}
}

func MCPHandler() http.Handler {
	server := mcp.NewServer(&mcp.Implementation{Name: "ops-copilot-tool-server", Version: "0.0.0"}, nil)
	registerMCPTools(server)
	jsonResponse := os.Getenv("MCP_JSON_RESPONSE") == "true"
	return mcp.NewStreamableHTTPHandler(func(*http.Request) *mcp.Server {
		return server
	}, &mcp.StreamableHTTPOptions{Stateless: true, JSONResponse: jsonResponse})
}

func registerMCPTools(server *mcp.Server) {
	mcp.AddTool(server, &mcp.Tool{Name: "k8s.list_pods", Description: "List pods in a namespace"},
		mcp.ToolHandlerFor[listPodsInput, toolResponse](func(ctx context.Context, request *mcp.CallToolRequest, input listPodsInput) (*mcp.CallToolResult, toolResponse, error) {
			payload := map[string]any{
				"namespace":      input.Namespace,
				"label_selector": input.LabelSelector,
			}
			addInternalArgs(payload, input.InstrumentationInput)
			resp := runToolRequest(ctx, "k8s.list_pods", payload)
			return nil, resp, nil
		}),
	)

	mcp.AddTool(server, &mcp.Tool{Name: "k8s.describe_pod", Description: "Describe a pod"},
		mcp.ToolHandlerFor[describePodInput, toolResponse](func(ctx context.Context, request *mcp.CallToolRequest, input describePodInput) (*mcp.CallToolResult, toolResponse, error) {
			payload := map[string]any{
				"namespace": input.Namespace,
				"pod_name":  input.PodName,
			}
			addInternalArgs(payload, input.InstrumentationInput)
			resp := runToolRequest(ctx, "k8s.describe_pod", payload)
			return nil, resp, nil
		}),
	)

	mcp.AddTool(server, &mcp.Tool{Name: "k8s.get_pod_events", Description: "Get pod events"},
		mcp.ToolHandlerFor[podEventsInput, toolResponse](func(ctx context.Context, request *mcp.CallToolRequest, input podEventsInput) (*mcp.CallToolResult, toolResponse, error) {
			payload := map[string]any{
				"namespace": input.Namespace,
				"pod_name":  input.PodName,
			}
			addInternalArgs(payload, input.InstrumentationInput)
			resp := runToolRequest(ctx, "k8s.get_pod_events", payload)
			return nil, resp, nil
		}),
	)

	mcp.AddTool(server, &mcp.Tool{Name: "k8s.get_pod_logs", Description: "Get pod logs"},
		mcp.ToolHandlerFor[podLogsInput, toolResponse](func(ctx context.Context, request *mcp.CallToolRequest, input podLogsInput) (*mcp.CallToolResult, toolResponse, error) {
			payload := map[string]any{
				"namespace": input.Namespace,
				"pod_name":  input.PodName,
			}
			if input.Container != "" {
				payload["container"] = input.Container
			}
			if input.TailLines > 0 {
				payload["tail_lines"] = input.TailLines
			}
			addInternalArgs(payload, input.InstrumentationInput)
			resp := runToolRequest(ctx, "k8s.get_pod_logs", payload)
			return nil, resp, nil
		}),
	)

	mcp.AddTool(server, &mcp.Tool{Name: "k8s.describe_deployment", Description: "Describe a deployment"},
		mcp.ToolHandlerFor[describeDeploymentInput, toolResponse](func(ctx context.Context, request *mcp.CallToolRequest, input describeDeploymentInput) (*mcp.CallToolResult, toolResponse, error) {
			payload := map[string]any{
				"namespace":       input.Namespace,
				"deployment_name": input.DeploymentName,
			}
			addInternalArgs(payload, input.InstrumentationInput)
			resp := runToolRequest(ctx, "k8s.describe_deployment", payload)
			return nil, resp, nil
		}),
	)
}

func runToolRequest(ctx context.Context, toolName string, args map[string]any) toolResponse {
	logging.Info(ctx, "mcp tool_call", "tool_name", toolName, "args", args)
	req := toolRequest{
		ToolName: toolName,
		Args:     args,
		Timeout:  toolTimeoutMs(),
	}
	resp := executeTool(req)
	logging.Info(ctx, "mcp tool_result", "tool_name", toolName, "status", resp.Status, "error", resp.Error)
	return resp
}

func toolTimeoutMs() int {
	value := os.Getenv("TOOL_TIMEOUT_MS")
	if value == "" {
		return 1000
	}
	n, err := strconv.Atoi(value)
	if err != nil {
		return 1000
	}
	return n
}
