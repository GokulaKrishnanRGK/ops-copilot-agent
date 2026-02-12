# Cluster Overview

The opscopilot local cluster is a Kind-based Kubernetes cluster used for integration tests.
The default namespace contains a hello deployment with an nginx container.

Common commands:
- kubectl get pods -n default
- kubectl describe pod hello -n default
- kubectl logs hello -n default
