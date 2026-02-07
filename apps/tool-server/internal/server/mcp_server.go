package server

import (
	"context"
	"net/http"
	"os"
	"strconv"

	mcp "github.com/modelcontextprotocol/go-sdk/mcp"
)

type listPodsInput struct {
	Namespace     string `json:"namespace"`
	LabelSelector string `json:"label_selector"`
}

type describePodInput struct {
	Namespace string `json:"namespace"`
	PodName   string `json:"pod_name"`
}

type podEventsInput struct {
	Namespace string `json:"namespace"`
	PodName   string `json:"pod_name"`
}

type podLogsInput struct {
	Namespace string `json:"namespace"`
	PodName   string `json:"pod_name"`
	Container string `json:"container"`
	TailLines int    `json:"tail_lines"`
}

type describeDeploymentInput struct {
	Namespace      string `json:"namespace"`
	DeploymentName string `json:"deployment_name"`
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
			resp := runToolRequest("k8s.list_pods", payload)
			return nil, resp, nil
		}),
	)

	mcp.AddTool(server, &mcp.Tool{Name: "k8s.describe_pod", Description: "Describe a pod"},
		mcp.ToolHandlerFor[describePodInput, toolResponse](func(ctx context.Context, request *mcp.CallToolRequest, input describePodInput) (*mcp.CallToolResult, toolResponse, error) {
			payload := map[string]any{
				"namespace": input.Namespace,
				"pod_name":  input.PodName,
			}
			resp := runToolRequest("k8s.describe_pod", payload)
			return nil, resp, nil
		}),
	)

	mcp.AddTool(server, &mcp.Tool{Name: "k8s.get_pod_events", Description: "Get pod events"},
		mcp.ToolHandlerFor[podEventsInput, toolResponse](func(ctx context.Context, request *mcp.CallToolRequest, input podEventsInput) (*mcp.CallToolResult, toolResponse, error) {
			payload := map[string]any{
				"namespace": input.Namespace,
				"pod_name":  input.PodName,
			}
			resp := runToolRequest("k8s.get_pod_events", payload)
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
			resp := runToolRequest("k8s.get_pod_logs", payload)
			return nil, resp, nil
		}),
	)

	mcp.AddTool(server, &mcp.Tool{Name: "k8s.describe_deployment", Description: "Describe a deployment"},
		mcp.ToolHandlerFor[describeDeploymentInput, toolResponse](func(ctx context.Context, request *mcp.CallToolRequest, input describeDeploymentInput) (*mcp.CallToolResult, toolResponse, error) {
			payload := map[string]any{
				"namespace":       input.Namespace,
				"deployment_name": input.DeploymentName,
			}
			resp := runToolRequest("k8s.describe_deployment", payload)
			return nil, resp, nil
		}),
	)
}

func runToolRequest(toolName string, args map[string]any) toolResponse {
	req := toolRequest{
		ToolName: toolName,
		Args:     args,
		Timeout:  toolTimeoutMs(),
	}
	return executeTool(req)
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
