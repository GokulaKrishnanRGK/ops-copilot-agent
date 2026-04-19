locals {
  app_target         = var.app_alb_dns_name
  grafana_target     = coalesce(var.observability_alb_dns_name, var.app_alb_dns_name, "")
  langfuse_target    = coalesce(var.langfuse_alb_dns_name, var.app_alb_dns_name, "")
  ttl                = var.proxied ? 1 : 60
}

data "cloudflare_zone" "this" {
  name = var.zone_name
}

resource "cloudflare_record" "app" {
  count = local.app_target != "" ? 1 : 0

  zone_id = data.cloudflare_zone.this.id
  name    = var.app_subdomain
  content = local.app_target
  type    = "CNAME"
  proxied = var.proxied
  ttl     = local.ttl
}

resource "cloudflare_record" "grafana" {
  count = local.grafana_target != "" ? 1 : 0

  zone_id = data.cloudflare_zone.this.id
  name    = var.grafana_subdomain
  content = local.grafana_target
  type    = "CNAME"
  proxied = var.proxied
  ttl     = local.ttl
}

resource "cloudflare_record" "langfuse" {
  count = local.langfuse_target != "" ? 1 : 0

  zone_id = data.cloudflare_zone.this.id
  name    = var.langfuse_subdomain
  content = local.langfuse_target
  type    = "CNAME"
  proxied = var.proxied
  ttl     = local.ttl
}
