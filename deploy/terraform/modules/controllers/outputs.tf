output "enabled" {
  description = "Whether controller IRSA roles are enabled."
  value       = local.enabled
}

output "external_dns_role_arn" {
  description = "IRSA role ARN for ExternalDNS."
  value       = local.enabled ? aws_iam_role.external_dns[0].arn : null
}

output "external_dns_role_name" {
  description = "IRSA role name for ExternalDNS."
  value       = local.enabled ? aws_iam_role.external_dns[0].name : null
}

output "aws_load_balancer_controller_role_arn" {
  description = "IRSA role ARN for AWS Load Balancer Controller."
  value       = local.enabled ? aws_iam_role.awslbc[0].arn : null
}

output "aws_load_balancer_controller_role_name" {
  description = "IRSA role name for AWS Load Balancer Controller."
  value       = local.enabled ? aws_iam_role.awslbc[0].name : null
}
