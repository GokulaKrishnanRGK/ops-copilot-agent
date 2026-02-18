output "network" {
  description = "Network contract outputs."
  value = {
    vpc_id                = module.network.vpc_id
    private_subnet_ids    = module.network.private_subnet_ids
    public_subnet_ids     = module.network.public_subnet_ids
    app_security_group_id = module.network.app_security_group_id
  }
}

output "rds" {
  description = "RDS contract outputs."
  value = {
    endpoint             = module.rds.endpoint
    port                 = module.rds.port
    database_secret_name = module.rds.database_secret_name
    database_secret_arn  = module.rds.database_secret_arn
    identifier           = module.rds.identifier
    database_name        = module.rds.database_name
    username             = module.rds.username
    security_group_id    = module.rds.security_group_id
  }
}

output "opensearch" {
  description = "OpenSearch contract outputs."
  value = {
    endpoint             = module.opensearch.endpoint
    username_secret_name = module.opensearch.username_secret_name
    password_secret_name = module.opensearch.password_secret_name
    domain_arn           = module.opensearch.domain_arn
    security_group_id    = module.opensearch.security_group_id
    username_secret_arn  = module.opensearch.username_secret_arn
    password_secret_arn  = module.opensearch.password_secret_arn
  }
}

output "artifacts" {
  description = "Artifact registry contract outputs."
  value = {
    ecr_repositories              = module.artifacts.ecr_repositories
    ecr_repository_urls           = module.artifacts.ecr_repository_urls
    ecr_repository_arns           = module.artifacts.ecr_repository_arns
    package_registry_url          = module.artifacts.package_registry_url
    package_registry_domain       = module.artifacts.package_registry_domain
    package_registry_repository   = module.artifacts.package_registry_repository
    package_registry_domain_owner = module.artifacts.package_registry_domain_owner
  }
}
