package k8s

import (
	"context"

	"k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
)

type DeploymentDetail struct {
	Name      string `json:"name"`
	Namespace string `json:"namespace"`
	Replicas  int32  `json:"replicas"`
	Ready     int32  `json:"ready"`
	Updated   int32  `json:"updated"`
	Available int32  `json:"available"`
}

func DescribeDeployment(ctx context.Context, client *kubernetes.Clientset, namespace string, deploymentName string) (DeploymentDetail, error) {
	dep, err := client.AppsV1().Deployments(namespace).Get(ctx, deploymentName, v1.GetOptions{})
	if err != nil {
		return DeploymentDetail{}, err
	}
	replicas := int32(0)
	if dep.Spec.Replicas != nil {
		replicas = *dep.Spec.Replicas
	}
	return DeploymentDetail{
		Name:      dep.Name,
		Namespace: dep.Namespace,
		Replicas:  replicas,
		Ready:     dep.Status.ReadyReplicas,
		Updated:   dep.Status.UpdatedReplicas,
		Available: dep.Status.AvailableReplicas,
	}, nil
}
