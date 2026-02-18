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

variable "vpc_cidr" {
  description = "VPC CIDR block."
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

variable "engine_version" {
  description = "PostgreSQL engine version."
  type        = string
  default     = "16.3"
}

variable "instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t3.micro"
}

variable "allocated_storage" {
  description = "Allocated storage in GiB."
  type        = number
  default     = 20
}

variable "max_allocated_storage" {
  description = "Maximum autoscaled storage in GiB."
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Initial database name."
  type        = string
  default     = "opscopilot"
}

variable "master_username" {
  description = "Master username for the PostgreSQL instance."
  type        = string
  default     = "opscopilot"
}

variable "backup_retention_period" {
  description = "Backup retention period in days."
  type        = number
  default     = 1
}

variable "deletion_protection" {
  description = "Enable deletion protection on the RDS instance."
  type        = bool
  default     = false
}

variable "skip_final_snapshot" {
  description = "Skip final snapshot on destroy."
  type        = bool
  default     = true
}
