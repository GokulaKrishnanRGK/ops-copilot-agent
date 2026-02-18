output "ecr_repositories" {
  description = "Container image repository names keyed by service."
  value       = local.ecr_repositories
}

output "ecr_repository_urls" {
  description = "Container image repository URLs keyed by service."
  value       = { for key, repo in aws_ecr_repository.service : key => repo.repository_url }
}

output "ecr_repository_arns" {
  description = "Container image repository ARNs keyed by service."
  value       = { for key, repo in aws_ecr_repository.service : key => repo.arn }
}

output "package_registry_url" {
  description = "Python package registry URL (when provisioned)."
  value       = local.package_registry_url
}

output "package_registry_domain" {
  description = "CodeArtifact domain name for Python package registry."
  value       = var.create_python_package_registry ? aws_codeartifact_domain.python[0].domain : null
}

output "package_registry_repository" {
  description = "CodeArtifact repository name for Python package registry."
  value       = var.create_python_package_registry ? aws_codeartifact_repository.python[0].repository : null
}

output "package_registry_domain_owner" {
  description = "AWS account ID that owns the package registry domain."
  value       = var.create_python_package_registry ? aws_codeartifact_domain.python[0].owner : null
}
