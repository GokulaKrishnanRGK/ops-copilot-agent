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

variable "eks_cluster_name" {
  description = "EKS cluster name. Defaults to <project>-<environment>-eks when empty."
  type        = string
  default     = ""
}

variable "eks_kubernetes_version" {
  description = "Kubernetes version for EKS."
  type        = string
  default     = "1.32"
}

variable "eks_node_instance_types" {
  description = "Managed node group instance types."
  type        = list(string)
  default     = ["t3.small"]
}

variable "eks_node_desired_size" {
  description = "Desired node count for the default managed node group."
  type        = number
  default     = 1
}

variable "eks_node_min_size" {
  description = "Minimum node count for the default managed node group."
  type        = number
  default     = 1
}

variable "eks_node_max_size" {
  description = "Maximum node count for the default managed node group."
  type        = number
  default     = 2
}

variable "eks_node_disk_size" {
  description = "Node root disk size (GiB) for the default managed node group."
  type        = number
  default     = 20
}

variable "eks_endpoint_public_access" {
  description = "Whether EKS API endpoint is publicly reachable."
  type        = bool
  default     = true
}

variable "eks_endpoint_private_access" {
  description = "Whether EKS API endpoint is privately reachable."
  type        = bool
  default     = false
}

variable "eks_public_access_cidrs" {
  description = "CIDRs allowed for public EKS API access."
  type        = list(string)
  default     = ["0.0.0.0/0"]
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
  description = "Primary DNS name for web ingress."
  type        = string
  default     = ""
}

variable "observability_domain_name" {
  description = "DNS name for observability ingress (Grafana)."
  type        = string
  default     = ""
}

variable "route53_hosted_zone_id" {
  description = "Route53 hosted zone ID for ingress record management."
  type        = string
  default     = ""
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN for ingress TLS termination."
  type        = string
  default     = ""
}

variable "controllers_create_irsa_roles" {
  description = "Create IRSA IAM roles/policies for cluster controllers."
  type        = bool
  default     = true
}

variable "eks_oidc_provider_arn" {
  description = "Deprecated: previously used for manual IRSA setup. Ignored when Terraform manages EKS."
  type        = string
  default     = ""
}

variable "eks_oidc_provider_url" {
  description = "Deprecated: previously used for manual IRSA setup. Ignored when Terraform manages EKS."
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
