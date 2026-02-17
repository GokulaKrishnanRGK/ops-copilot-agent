output "endpoint" {
  description = "RDS endpoint hostname."
  value       = local.endpoint
}

output "port" {
  description = "RDS port."
  value       = local.port
}

output "database_secret_name" {
  description = "Secret name containing DB credentials/URL."
  value       = var.database_secret_name
}
