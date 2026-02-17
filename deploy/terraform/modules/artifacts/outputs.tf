output "ecr_repositories" {
  description = "Container image repository names keyed by service."
  value       = local.ecr_repositories
}

output "package_registry_url" {
  description = "Python package registry URL (when provisioned)."
  value       = local.package_registry_url
}
