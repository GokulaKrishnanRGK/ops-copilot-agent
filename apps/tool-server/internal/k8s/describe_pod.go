package k8s

import (
	"context"

	"k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
)

type PodDetail struct {
	Name      string `json:"name"`
	Namespace string `json:"namespace"`
	Phase     string `json:"phase"`
	Node      string `json:"node"`
	Reason    string `json:"reason"`
	Message   string `json:"message"`
	StartTime string `json:"start_time"`
}

func DescribePod(ctx context.Context, client *kubernetes.Clientset, namespace string, podName string) (PodDetail, error) {
	pod, err := client.CoreV1().Pods(namespace).Get(ctx, podName, v1.GetOptions{})
	if err != nil {
		return PodDetail{}, err
	}
	start := ""
	if pod.Status.StartTime != nil {
		start = pod.Status.StartTime.UTC().Format("2006-01-02T15:04:05Z")
	}
	return PodDetail{
		Name:      pod.Name,
		Namespace: pod.Namespace,
		Phase:     string(pod.Status.Phase),
		Node:      pod.Spec.NodeName,
		Reason:    pod.Status.Reason,
		Message:   pod.Status.Message,
		StartTime: start,
	}, nil
}
