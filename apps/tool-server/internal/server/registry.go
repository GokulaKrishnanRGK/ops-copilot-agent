package server

import (
	"context"
	"os"
	"sort"

	"github.com/ops-copilot/tool-server/internal/k8s"
	"github.com/ops-copilot/tool-server/internal/logging"
	"k8s.io/client-go/kubernetes"
)

type toolHandler func(ctx context.Context, client *kubernetes.Clientset, args map[string]any) (any, *toolError)

var toolRegistry = map[string]toolHandler{
	"k8s.list_pods":           listPodsHandler,
	"k8s.list_namespaces":     listNamespacesHandler,
	"k8s.describe_pod":        describePodHandler,
	"k8s.get_pod_events":      podEventsHandler,
	"k8s.get_pod_logs":        podLogsHandler,
	"k8s.describe_deployment": describeDeploymentHandler,
}

func listPodsHandler(ctx context.Context, client *kubernetes.Clientset, args map[string]any) (any, *toolError) {
	labelSelector, _ := args["label_selector"].(string)
	namespace, _ := args["namespace"].(string)
	pods, err := k8s.ListPods(ctx, client, namespace, labelSelector)
	if err != nil {
		logging.Error(ctx, "tool error", "tool_name", "k8s.list_pods", "error", err)
		errResp := toolError{
			ErrorType: "execution_error",
			Message:   "list pods failed: " + err.Error(),
			ToolName:  "k8s.list_pods",
			Duration:  0,
		}
		return nil, &errResp
	}
	return map[string]any{
		"tool_name": "k8s.list_pods",
		"items":     pods,
	}, nil
}

func listNamespacesHandler(ctx context.Context, client *kubernetes.Clientset, args map[string]any) (any, *toolError) {
	allowedMap := k8s.ParseAllowlist(os.Getenv("K8S_ALLOWED_NAMESPACES"))
	if len(allowedMap) == 0 {
		errResp := toolError{
			ErrorType: "permission_denied",
			Message:   "no allowed namespaces configured",
			ToolName:  "k8s.list_namespaces",
			Duration:  0,
		}
		return nil, &errResp
	}

	allowedNamespaces := make([]string, 0, len(allowedMap))
	for namespace := range allowedMap {
		allowedNamespaces = append(allowedNamespaces, namespace)
	}
	sort.Strings(allowedNamespaces)

	candidates := allowedNamespaces
	clusterNamespaces, err := k8s.ListNamespaces(ctx, client)
	if err == nil {
		clusterSet := make(map[string]struct{}, len(clusterNamespaces))
		for _, namespace := range clusterNamespaces {
			clusterSet[namespace] = struct{}{}
		}
		candidates = make([]string, 0, len(allowedNamespaces))
		for _, namespace := range allowedNamespaces {
			if _, ok := clusterSet[namespace]; ok {
				candidates = append(candidates, namespace)
			}
		}
	}

	accessible := k8s.FilterAccessibleNamespaces(ctx, client, candidates)
	return map[string]any{
		"tool_name":           "k8s.list_namespaces",
		"allowed_namespaces":  allowedNamespaces,
		"matching_namespaces": accessible,
		"items":               accessible,
	}, nil
}

func describePodHandler(ctx context.Context, client *kubernetes.Clientset, args map[string]any) (any, *toolError) {
	namespace, _ := args["namespace"].(string)
	podName, _ := args["pod_name"].(string)
	if podName == "" {
		errResp := toolError{
			ErrorType: "invalid_input",
			Message:   "pod_name required",
			ToolName:  "k8s.describe_pod",
			Duration:  0,
		}
		return nil, &errResp
	}
	pod, err := k8s.DescribePod(ctx, client, namespace, podName)
	if err != nil {
		logging.Error(ctx, "tool error", "tool_name", "k8s.describe_pod", "error", err)
		errResp := toolError{
			ErrorType: "execution_error",
			Message:   "describe pod failed: " + err.Error(),
			ToolName:  "k8s.describe_pod",
			Duration:  0,
		}
		return nil, &errResp
	}
	return map[string]any{
		"tool_name": "k8s.describe_pod",
		"pod":       pod,
	}, nil
}

func podEventsHandler(ctx context.Context, client *kubernetes.Clientset, args map[string]any) (any, *toolError) {
	namespace, _ := args["namespace"].(string)
	podName, _ := args["pod_name"].(string)
	if podName == "" {
		errResp := toolError{
			ErrorType: "invalid_input",
			Message:   "pod_name required",
			ToolName:  "k8s.get_pod_events",
			Duration:  0,
		}
		return nil, &errResp
	}
	events, err := k8s.GetPodEvents(ctx, client, namespace, podName)
	if err != nil {
		logging.Error(ctx, "tool error", "tool_name", "k8s.get_pod_events", "error", err)
		errResp := toolError{
			ErrorType: "execution_error",
			Message:   "get pod events failed: " + err.Error(),
			ToolName:  "k8s.get_pod_events",
			Duration:  0,
		}
		return nil, &errResp
	}
	return map[string]any{
		"tool_name": "k8s.get_pod_events",
		"events":    events,
	}, nil
}

func podLogsHandler(ctx context.Context, client *kubernetes.Clientset, args map[string]any) (any, *toolError) {
	namespace, _ := args["namespace"].(string)
	podName, _ := args["pod_name"].(string)
	if podName == "" {
		errResp := toolError{
			ErrorType: "invalid_input",
			Message:   "pod_name required",
			ToolName:  "k8s.get_pod_logs",
			Duration:  0,
		}
		return nil, &errResp
	}
	container, _ := args["container"].(string)
	tailLines := int64(100)
	if raw, ok := args["tail_lines"].(float64); ok {
		tailLines = int64(raw)
	}
	logs, err := k8s.GetPodLogs(ctx, client, namespace, podName, container, tailLines)
	if err != nil {
		logging.Error(ctx, "tool error", "tool_name", "k8s.get_pod_logs", "error", err)
		errResp := toolError{
			ErrorType: "execution_error",
			Message:   "get pod logs failed: " + err.Error(),
			ToolName:  "k8s.get_pod_logs",
			Duration:  0,
		}
		return nil, &errResp
	}
	return map[string]any{
		"tool_name": "k8s.get_pod_logs",
		"logs":      logs.Text,
	}, nil
}

func describeDeploymentHandler(ctx context.Context, client *kubernetes.Clientset, args map[string]any) (any, *toolError) {
	namespace, _ := args["namespace"].(string)
	deploymentName, _ := args["deployment_name"].(string)
	if deploymentName == "" {
		errResp := toolError{
			ErrorType: "invalid_input",
			Message:   "deployment_name required",
			ToolName:  "k8s.describe_deployment",
			Duration:  0,
		}
		return nil, &errResp
	}
	deployment, err := k8s.DescribeDeployment(ctx, client, namespace, deploymentName)
	if err != nil {
		logging.Error(ctx, "tool error", "tool_name", "k8s.describe_deployment", "error", err)
		errResp := toolError{
			ErrorType: "execution_error",
			Message:   "describe deployment failed: " + err.Error(),
			ToolName:  "k8s.describe_deployment",
			Duration:  0,
		}
		return nil, &errResp
	}
	return map[string]any{
		"tool_name":  "k8s.describe_deployment",
		"deployment": deployment,
	}, nil
}
