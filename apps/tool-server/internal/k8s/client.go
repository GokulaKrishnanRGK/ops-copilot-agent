package k8s

import (
	"os"

	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
)

func NewClient() (*kubernetes.Clientset, error) {
	cfg, err := rest.InClusterConfig()
	if err == nil {
		return kubernetes.NewForConfig(cfg)
	}
	kubeconfig := os.Getenv("KUBECONFIG_PATH")
	if kubeconfig == "" {
		kubeconfig = os.Getenv("KUBECONFIG")
	}
	if kubeconfig == "" {
		return nil, err
	}
	cfg, err = clientcmd.BuildConfigFromFlags("", kubeconfig)
	if err != nil {
		return nil, err
	}
	if os.Getenv("K8S_INSECURE_SKIP_TLS_VERIFY") == "1" {
		cfg.TLSClientConfig.Insecure = true
		cfg.TLSClientConfig.CAData = nil
		cfg.TLSClientConfig.CAFile = ""
	}
	return kubernetes.NewForConfig(cfg)
}
