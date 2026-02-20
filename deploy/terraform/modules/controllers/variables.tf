variable "create" {
  description = "Whether to create IRSA IAM roles/policies for cluster controllers."
  type        = bool
  default     = false
}

variable "name_prefix" {
  description = "Resource name prefix."
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources."
  type        = map(string)
  default     = {}
}

variable "oidc_provider_arn" {
  description = "EKS OIDC provider ARN used for IRSA trust policies."
  type        = string
  default     = ""
}

variable "oidc_provider_url" {
  description = "EKS OIDC issuer URL used for IRSA trust conditions."
  type        = string
  default     = ""
}

variable "external_dns_namespace" {
  description = "Namespace for ExternalDNS service account."
  type        = string
  default     = "external-dns"
}

variable "external_dns_service_account_name" {
  description = "Service account name for ExternalDNS."
  type        = string
  default     = "external-dns"
}

variable "aws_load_balancer_controller_namespace" {
  description = "Namespace for AWS Load Balancer Controller service account."
  type        = string
  default     = "kube-system"
}

variable "aws_load_balancer_controller_service_account_name" {
  description = "Service account name for AWS Load Balancer Controller."
  type        = string
  default     = "aws-load-balancer-controller"
}
