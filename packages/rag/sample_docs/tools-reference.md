# Tool Reference

Available MCP tools for the tool-server:

- k8s.list_pods: List pods in a namespace. Requires namespace and label_selector.
- k8s.describe_pod: Describe a pod. Requires namespace and pod_name.
- k8s.get_pod_logs: Get pod logs. Requires namespace, pod_name, container, tail_lines.
- k8s.get_pod_events: Get pod events. Requires namespace and pod_name.
- k8s.describe_deployment: Describe a deployment. Requires namespace and deployment_name.

If a required argument is missing, the agent should ask a clarifying question.
