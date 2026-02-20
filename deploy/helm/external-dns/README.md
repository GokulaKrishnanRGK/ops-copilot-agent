# ExternalDNS Helm Chart

This chart installs ExternalDNS for Route53 automation from Kubernetes ingress resources.

## Prerequisites

- EKS cluster with OIDC provider enabled.
- IAM role for service account (IRSA) allowing Route53 record changes for target zones.
- AWS Load Balancer Controller installed.

## Deploy

1. Generate values from Terraform outputs:

```bash
make helm-controller-values-generate
```

2. Deploy:

```bash
make helm-externaldns-up
```

## Remove

```bash
make helm-externaldns-down
```

## Notes

- Use `--registry=txt` with unique `txtOwnerId` to avoid DNS ownership conflicts.
- Set `domainFilters` and optional `zone-id-filter` to prevent unwanted record changes.
- By default `make helm-externaldns-up` auto-generates `deploy/helm/external-dns/values-eks.generated.yaml` when `HELM_EXTERNALDNS_VALUES_FILE` is not set.
