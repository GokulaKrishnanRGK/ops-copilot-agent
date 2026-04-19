output "secret_name" {
  description = "Name of the Secrets Manager secret containing Langfuse keys."
  value       = aws_secretsmanager_secret.langfuse.name
}

output "secret_arn" {
  description = "ARN of the Secrets Manager secret containing Langfuse keys."
  value       = aws_secretsmanager_secret.langfuse.arn
}
