locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = merge(
    {
      project     = var.project_name
      environment = var.environment
      managed_by  = "terraform"
    },
    var.tags
  )

  app_fqdn      = "opscopilot.${var.cloudflare_zone_name}"
  grafana_fqdn  = "grafana.${var.cloudflare_zone_name}"
  langfuse_fqdn = "langfuse.${var.cloudflare_zone_name}"

  dns_ready = var.app_alb_dns_name != ""
}
