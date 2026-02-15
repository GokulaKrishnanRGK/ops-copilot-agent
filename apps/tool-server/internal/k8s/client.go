package k8s

import (
	"fmt"
	"os"

	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
)

func NewClient() (*kubernetes.Clientset, error) {
	kubeconfig := os.Getenv("KUBECONFIG_PATH")
	if kubeconfig == "" {
		kubeconfig = os.Getenv("KUBECONFIG")
	}
	if kubeconfig != "" {
		cfg, err := clientcmd.BuildConfigFromFlags("", kubeconfig)
		if err != nil {
			return nil, fmt.Errorf("load kubeconfig from %q: %w", kubeconfig, err)
		}
		if os.Getenv("K8S_INSECURE_SKIP_TLS_VERIFY") == "1" {
			cfg.TLSClientConfig.Insecure = true
			cfg.TLSClientConfig.CAData = nil
			cfg.TLSClientConfig.CAFile = ""
		}
		return kubernetes.NewForConfig(cfg)
	}

	cfg, inClusterErr := rest.InClusterConfig()
	if inClusterErr == nil {
		return kubernetes.NewForConfig(cfg)
	}

	loadingRules := clientcmd.NewDefaultClientConfigLoadingRules()
	localCfg, localErr := clientcmd.NewNonInteractiveDeferredLoadingClientConfig(
		loadingRules,
		&clientcmd.ConfigOverrides{},
	).ClientConfig()
	if localErr != nil {
		return nil, fmt.Errorf(
			"no usable Kubernetes config found (in-cluster: %v, local: %v); set KUBECONFIG_PATH or KUBECONFIG",
			inClusterErr,
			localErr,
		)
	}
	cfg = localCfg
	if os.Getenv("K8S_INSECURE_SKIP_TLS_VERIFY") == "1" {
		cfg.TLSClientConfig.Insecure = true
		cfg.TLSClientConfig.CAData = nil
		cfg.TLSClientConfig.CAFile = ""
	}
	return kubernetes.NewForConfig(cfg)
}
