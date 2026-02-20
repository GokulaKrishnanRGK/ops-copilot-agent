variable "name_prefix" {
  description = "Resource name prefix."
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources."
  type        = map(string)
  default     = {}
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for EKS control plane and node group."
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "Private subnet IDs used for subnet tagging compatibility."
  type        = list(string)
}

variable "cluster_name" {
  description = "EKS cluster name."
  type        = string
}

variable "kubernetes_version" {
  description = "Kubernetes version for the EKS control plane."
  type        = string
}

variable "node_instance_types" {
  description = "Managed node group instance types."
  type        = list(string)
}

variable "node_desired_size" {
  description = "Desired node count for the default managed node group."
  type        = number
}

variable "node_min_size" {
  description = "Minimum node count for the default managed node group."
  type        = number
}

variable "node_max_size" {
  description = "Maximum node count for the default managed node group."
  type        = number
}

variable "node_disk_size" {
  description = "Node root volume size in GiB."
  type        = number
}

variable "endpoint_public_access" {
  description = "Whether EKS API endpoint is publicly reachable."
  type        = bool
}

variable "endpoint_private_access" {
  description = "Whether EKS API endpoint is privately reachable."
  type        = bool
}

variable "public_access_cidrs" {
  description = "CIDRs allowed to access the public EKS API endpoint."
  type        = list(string)
}
