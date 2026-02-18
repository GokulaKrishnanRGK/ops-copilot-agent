output "endpoint" {
  description = "OpenSearch endpoint URL/hostname."
  value       = local.endpoint
}

output "username_secret_name" {
  description = "Secret name containing OpenSearch username."
  value       = aws_secretsmanager_secret.username.name
}

output "password_secret_name" {
  description = "Secret name containing OpenSearch password."
  value       = aws_secretsmanager_secret.password.name
}

output "domain_arn" {
  description = "OpenSearch domain ARN."
  value       = aws_opensearch_domain.this.arn
}

output "security_group_id" {
  description = "OpenSearch security group ID."
  value       = aws_security_group.opensearch.id
}

output "username_secret_arn" {
  description = "ARN of username secret."
  value       = aws_secretsmanager_secret.username.arn
}

output "password_secret_arn" {
  description = "ARN of password secret."
  value       = aws_secretsmanager_secret.password.arn
}
