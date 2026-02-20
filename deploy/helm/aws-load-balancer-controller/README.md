# AWS Load Balancer Controller (Helm)

This directory contains values for installing the AWS Load Balancer Controller from the official EKS Helm chart.

Chart source:
- Repository: `https://aws.github.io/eks-charts`
- Chart: `eks/aws-load-balancer-controller`

## Prerequisites

- EKS cluster and `kubectl` context configured.
- IAM OIDC provider enabled for the cluster.
- IRSA IAM role for controller service account with required permissions.

## Configure

Generate:

```bash
make helm-controller-values-generate
```

Optional override:
- `HELM_AWSLBC_CLUSTER_NAME=<cluster-name>` (only needed if Terraform output is unavailable)

This writes:
- `deploy/helm/aws-load-balancer-controller/values-eks.generated.yaml`

## Install

```bash
make helm-awslbc-up
```

By default `make helm-awslbc-up` auto-generates controller values when `HELM_AWSLBC_VALUES_FILE` is not set.

## Uninstall

```bash
make helm-awslbc-down
```
