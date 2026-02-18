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

variable "engine_version" {
  description = "OpenSearch engine version."
  type        = string
  default     = "OpenSearch_2.13"
}

variable "instance_type" {
  description = "OpenSearch data node instance type."
  type        = string
  default     = "t3.small.search"
}

variable "instance_count" {
  description = "Number of OpenSearch data nodes."
  type        = number
  default     = 1
}

variable "volume_size" {
  description = "EBS volume size in GiB."
  type        = number
  default     = 20
}

variable "master_username" {
  description = "Master username for fine-grained access control."
  type        = string
  default     = "opscopilot"
}
