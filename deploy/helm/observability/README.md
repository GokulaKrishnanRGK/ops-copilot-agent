# Observability Helm Chart

This chart deploys the OpsCopilot observability stack to Kubernetes:
- Loki
- Tempo
- Prometheus
- Grafana
- Alloy (log collection)
- OpenTelemetry Collector

## Local kind deployment

```bash
helm upgrade --install opscopilot-observability deploy/helm/observability \
  -n opscopilot-local --create-namespace \
  -f deploy/helm/observability/values-local-kind.yaml
```

## EKS deployment with subdomain ingress

Set Terraform values:
- `observability_domain_name = "observe.<your-domain>"`
- `route53_hosted_zone_id = "..."`
- `acm_certificate_arn = "..."`

Then deploy with ingress enabled:

```bash
helm upgrade --install opscopilot-observability deploy/helm/observability \
  -n opscopilot --create-namespace \
  -f deploy/helm/observability/values-terraform-example.yaml
```
