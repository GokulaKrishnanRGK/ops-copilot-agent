output "cluster_name" {
  description = "EKS cluster name."
  value       = aws_eks_cluster.this.name
}

output "cluster_arn" {
  description = "EKS cluster ARN."
  value       = aws_eks_cluster.this.arn
}

output "cluster_endpoint" {
  description = "EKS control plane endpoint."
  value       = aws_eks_cluster.this.endpoint
}

output "cluster_version" {
  description = "EKS Kubernetes version."
  value       = aws_eks_cluster.this.version
}

output "cluster_ca_data" {
  description = "Base64 cluster certificate authority data."
  value       = aws_eks_cluster.this.certificate_authority[0].data
}

output "oidc_provider_arn" {
  description = "IAM OIDC provider ARN for IRSA."
  value       = aws_iam_openid_connect_provider.this.arn
}

output "oidc_issuer_url" {
  description = "OIDC issuer URL used by EKS."
  value       = aws_eks_cluster.this.identity[0].oidc[0].issuer
}

output "node_group_name" {
  description = "Default managed node group name."
  value       = aws_eks_node_group.default.node_group_name
}
