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
  }
}

output "opensearch" {
  description = "OpenSearch contract outputs."
  value = {
    endpoint             = module.opensearch.endpoint
    username_secret_name = module.opensearch.username_secret_name
    password_secret_name = module.opensearch.password_secret_name
  }
}

output "artifacts" {
  description = "Artifact registry contract outputs."
  value = {
    ecr_repositories     = module.artifacts.ecr_repositories
    package_registry_url = module.artifacts.package_registry_url
  }
}
