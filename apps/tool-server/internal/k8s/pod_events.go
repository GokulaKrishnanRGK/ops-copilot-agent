package k8s

import (
	"context"

	"k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
)

type PodEvent struct {
	Reason  string `json:"reason"`
	Message string `json:"message"`
	Type    string `json:"type"`
	Time    string `json:"time"`
}

func GetPodEvents(ctx context.Context, client *kubernetes.Clientset, namespace string, podName string) ([]PodEvent, error) {
	selector := "involvedObject.name=" + podName
	events, err := client.CoreV1().Events(namespace).List(ctx, v1.ListOptions{FieldSelector: selector})
	if err != nil {
		return nil, err
	}
	items := make([]PodEvent, 0, len(events.Items))
	for _, evt := range events.Items {
		timeStr := ""
		if evt.LastTimestamp.Time.IsZero() {
			timeStr = evt.EventTime.Time.UTC().Format("2006-01-02T15:04:05Z")
		} else {
			timeStr = evt.LastTimestamp.Time.UTC().Format("2006-01-02T15:04:05Z")
		}
		items = append(items, PodEvent{
			Reason:  evt.Reason,
			Message: evt.Message,
			Type:    evt.Type,
			Time:    timeStr,
		})
	}
	return items, nil
}
