variable "aws_region" {
  description = "AWS region for infrastructure resources."
  type        = string
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
