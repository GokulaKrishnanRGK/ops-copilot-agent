variable "aws_region" {
  description = "AWS region for infrastructure resources."
  type        = string
}

variable "aws_profile" {
  description = "AWS CLI profile used by Terraform provider."
  type        = string
  default     = "default"
}

variable "project_name" {
  description = "Project identifier used in resource naming."
  type        = string
  default     = "ops-copilot"
}

variable "environment" {
  description = "Environment name (for example: dev, staging, prod)."
  type        = string
  default     = "dev"
}

variable "tags" {
  description = "Additional tags applied to all managed resources."
  type        = map(string)
  default     = {}
}

variable "network_vpc_cidr" {
  description = "CIDR block for the primary VPC."
  type        = string
  default     = "10.42.0.0/16"
}

variable "network_az_count" {
  description = "Number of availability zones used for subnet placement."
  type        = number
  default     = 2

  validation {
    condition     = var.network_az_count >= 2
    error_message = "network_az_count must be at least 2."
  }
}

variable "opensearch_index_name" {
  description = "Default OpenSearch index name consumed by application runtime."
  type        = string
  default     = "opscopilot-docs"
}

variable "artifacts_create_python_package_registry" {
  description = "Create CodeArtifact domain and repository for Python packages."
  type        = bool
  default     = false
}

variable "artifacts_ecr_scan_on_push" {
  description = "Enable ECR image scan on push."
  type        = bool
  default     = false
}

variable "ingress_domain_name" {
  description = "Primary DNS name for web ingress (contract placeholder for M12)."
  type        = string
  default     = ""
}

variable "route53_hosted_zone_id" {
  description = "Route53 hosted zone ID for ingress record management (contract placeholder for M12)."
  type        = string
  default     = ""
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN for ingress TLS termination (contract placeholder for M12)."
  type        = string
  default     = ""
}
