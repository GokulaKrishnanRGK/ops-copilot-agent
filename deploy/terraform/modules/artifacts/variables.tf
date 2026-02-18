variable "name_prefix" {
  description = "Resource name prefix."
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources."
  type        = map(string)
}

variable "ecr_image_tag_mutability" {
  description = "Image tag mutability policy for ECR repositories."
  type        = string
  default     = "MUTABLE"
}

variable "ecr_scan_on_push" {
  description = "Enable ECR image scanning on push."
  type        = bool
  default     = true
}

variable "create_python_package_registry" {
  description = "Create CodeArtifact domain/repository for Python packages."
  type        = bool
  default     = true
}

variable "codeartifact_domain_name" {
  description = "Optional override for CodeArtifact domain name."
  type        = string
  default     = ""
}

variable "codeartifact_repository_name" {
  description = "CodeArtifact repository name for Python packages."
  type        = string
  default     = "python-internal"
}
