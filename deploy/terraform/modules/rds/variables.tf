variable "name_prefix" {
  description = "Resource name prefix."
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources."
  type        = map(string)
}

variable "vpc_id" {
  description = "VPC identifier."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet identifiers."
  type        = list(string)
}

variable "security_group_id" {
  description = "Application security group identifier."
  type        = string
}

variable "database_secret_name" {
  description = "Secret name that will hold DB connection material."
  type        = string
}
