package k8s

import (
	"context"

	corev1 "k8s.io/api/core/v1"
	"k8s.io/client-go/kubernetes"
)

type PodLogs struct {
	Text string `json:"text"`
}

func GetPodLogs(ctx context.Context, client *kubernetes.Clientset, namespace string, podName string, container string, tailLines int64) (PodLogs, error) {
	req := client.CoreV1().Pods(namespace).GetLogs(podName, &corev1.PodLogOptions{Container: container, TailLines: &tailLines})
	data, err := req.DoRaw(ctx)
	if err != nil {
		return PodLogs{}, err
	}
	return PodLogs{Text: string(data)}, nil
}
