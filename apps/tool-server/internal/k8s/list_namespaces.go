package k8s

import (
	"context"
	"sort"

	v1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
)

func ListNamespaces(ctx context.Context, client *kubernetes.Clientset) ([]string, error) {
	namespaces, err := client.CoreV1().Namespaces().List(ctx, v1.ListOptions{})
	if err != nil {
		return nil, err
	}
	items := make([]string, 0, len(namespaces.Items))
	for _, ns := range namespaces.Items {
		items = append(items, ns.Name)
	}
	sort.Strings(items)
	return items, nil
}

func FilterAccessibleNamespaces(ctx context.Context, client *kubernetes.Clientset, namespaces []string) []string {
	accessible := make([]string, 0, len(namespaces))
	for _, namespace := range namespaces {
		_, err := client.CoreV1().Pods(namespace).List(ctx, v1.ListOptions{Limit: 1})
		if err != nil {
			continue
		}
		accessible = append(accessible, namespace)
	}
	sort.Strings(accessible)
	return accessible
}
