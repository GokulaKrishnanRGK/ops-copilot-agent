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
