output "vpc_id" {
  description = "VPC identifier."
  value       = aws_vpc.this.id
}

output "private_subnet_ids" {
  description = "Private subnet identifiers."
  value       = [for az in sort(keys(aws_subnet.private)) : aws_subnet.private[az].id]
}

output "public_subnet_ids" {
  description = "Public subnet identifiers."
  value       = [for az in sort(keys(aws_subnet.public)) : aws_subnet.public[az].id]
}

output "app_security_group_id" {
  description = "Application security group identifier."
  value       = aws_security_group.app.id
}
