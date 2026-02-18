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

output "helm_values" {
  description = "Normalized non-sensitive values contract for Helm consumption."
  value = {
    global = {
      awsRegion = var.aws_region
    }
    images = {
      apiRepository        = module.artifacts.ecr_repository_urls.api
      webRepository        = module.artifacts.ecr_repository_urls.web
      toolServerRepository = module.artifacts.ecr_repository_urls.tool_server
    }
    api = {
      env = {
        opensearchUrl   = "https://${module.opensearch.endpoint}"
        opensearchIndex = var.opensearch_index_name
      }
      infra = {
        rdsEndpoint = module.rds.endpoint
        rdsPort     = module.rds.port
        rdsDatabase = module.rds.database_name
      }
    }
    artifacts = {
      pythonPackageRegistryUrl = module.artifacts.package_registry_url
    }
  }
}

output "helm_secret_refs" {
  description = "Normalized secret-reference contract for Helm consumption."
  value = {
    api = {
      database = {
        secretName = module.rds.database_secret_name
        secretArn  = module.rds.database_secret_arn
      }
      opensearch = {
        usernameSecretName = module.opensearch.username_secret_name
        passwordSecretName = module.opensearch.password_secret_name
        usernameSecretArn  = module.opensearch.username_secret_arn
        passwordSecretArn  = module.opensearch.password_secret_arn
      }
    }
  }
}

output "terraform_output_contract_version" {
  description = "Version marker for Terraform->Helm normalized output contract."
  value       = "v1"
}
