output "endpoint" {
  description = "OpenSearch endpoint URL/hostname."
  value       = local.endpoint
}

output "username_secret_name" {
  description = "Secret name containing OpenSearch username."
  value       = local.username_secret_name
}

output "password_secret_name" {
  description = "Secret name containing OpenSearch password."
  value       = local.password_secret_name
}
