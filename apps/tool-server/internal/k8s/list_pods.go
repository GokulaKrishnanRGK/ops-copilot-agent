package k8s

import (
	"context"

	"k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
)

type PodSummary struct {
	Name      string `json:"name"`
	Namespace string `json:"namespace"`
	Status    string `json:"status"`
	Node      string `json:"node"`
}

func ListPods(ctx context.Context, client *kubernetes.Clientset, namespace string, labelSelector string) ([]PodSummary, error) {
	options := v1.ListOptions{}
	if labelSelector != "" {
		options.LabelSelector = labelSelector
	}
	pods, err := client.CoreV1().Pods(namespace).List(ctx, options)
	if err != nil {
		return nil, err
	}
	items := make([]PodSummary, 0, len(pods.Items))
	for _, pod := range pods.Items {
		items = append(items, PodSummary{
			Name:      pod.Name,
			Namespace: pod.Namespace,
			Status:    string(pod.Status.Phase),
			Node:      pod.Spec.NodeName,
		})
	}
	return items, nil
}
