output "vpc_id" {
  description = "VPC identifier."
  value       = local.vpc_id
}

output "private_subnet_ids" {
  description = "Private subnet identifiers."
  value       = []
}

output "public_subnet_ids" {
  description = "Public subnet identifiers."
  value       = []
}

output "app_security_group_id" {
  description = "Application security group identifier."
  value       = null
}
