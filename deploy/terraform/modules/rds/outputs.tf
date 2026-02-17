output "endpoint" {
  description = "RDS endpoint hostname."
  value       = aws_db_instance.this.address
}

output "port" {
  description = "RDS port."
  value       = aws_db_instance.this.port
}

output "database_secret_name" {
  description = "Secret name containing DB credentials/URL."
  value       = var.database_secret_name
}

output "database_secret_arn" {
  description = "ARN of the AWS-managed master user secret."
  value       = try(aws_db_instance.this.master_user_secret[0].secret_arn, null)
}

output "identifier" {
  description = "RDS instance identifier."
  value       = aws_db_instance.this.identifier
}

output "database_name" {
  description = "Primary database name."
  value       = aws_db_instance.this.db_name
}

output "username" {
  description = "Master username."
  value       = aws_db_instance.this.username
}

output "security_group_id" {
  description = "Database security group ID."
  value       = aws_security_group.db.id
}
