variable "zone_name" {
  description = "Cloudflare zone name (root domain, e.g. gokulakrishnanr.com)."
  type        = string
}

variable "app_subdomain" {
  description = "Subdomain for the main application."
  type        = string
  default     = "opscopilot"
}

variable "grafana_subdomain" {
  description = "Subdomain for Grafana observability."
  type        = string
  default     = "grafana"
}

variable "langfuse_subdomain" {
  description = "Subdomain for Langfuse."
  type        = string
  default     = "langfuse"
}

variable "app_alb_dns_name" {
  description = "AWS ALB DNS name for the application. Records are skipped when empty."
  type        = string
  default     = ""
}

variable "observability_alb_dns_name" {
  description = "AWS ALB DNS name for observability (Grafana). Falls back to app_alb_dns_name when empty."
  type        = string
  default     = ""
}

variable "langfuse_alb_dns_name" {
  description = "AWS ALB DNS name for Langfuse. Falls back to app_alb_dns_name when empty."
  type        = string
  default     = ""
}

variable "proxied" {
  description = "Whether Cloudflare proxies traffic (orange cloud). Enables Cloudflare edge SSL — origin ALB serves HTTP only."
  type        = bool
  default     = true
}
