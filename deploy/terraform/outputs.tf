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

output "eks" {
  description = "EKS contract outputs."
  value = {
    cluster_name      = module.eks.cluster_name
    cluster_arn       = module.eks.cluster_arn
    cluster_endpoint  = module.eks.cluster_endpoint
    cluster_version   = module.eks.cluster_version
    cluster_ca_data   = module.eks.cluster_ca_data
    oidc_provider_arn = module.eks.oidc_provider_arn
    oidc_issuer_url   = module.eks.oidc_issuer_url
    node_group_name   = module.eks.node_group_name
  }
}

output "controllers" {
  description = "Controller IRSA role contract outputs."
  value = {
    enabled = module.controllers.enabled
    external_dns = {
      role_arn             = module.controllers.external_dns_role_arn
      role_name            = module.controllers.external_dns_role_name
      namespace            = var.external_dns_namespace
      service_account_name = var.external_dns_service_account_name
    }
    aws_load_balancer_controller = {
      role_arn             = module.controllers.aws_load_balancer_controller_role_arn
      role_name            = module.controllers.aws_load_balancer_controller_role_name
      namespace            = var.aws_load_balancer_controller_namespace
      service_account_name = var.aws_load_balancer_controller_service_account_name
    }
  }
}

output "helm_values" {
  description = "Normalized non-sensitive values contract for Helm consumption."
  value = {
    global = {
      awsRegion = var.aws_region
    }
    eks = {
      clusterName = module.eks.cluster_name
      vpcId       = module.network.vpc_id
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
    ingress = {
      domainName = var.ingress_domain_name != "" ? var.ingress_domain_name : null
      tls = {
        certificateArn = var.acm_certificate_arn != "" ? var.acm_certificate_arn : null
      }
    }
    observability = {
      grafana = {
        domainName = var.observability_domain_name != "" ? var.observability_domain_name : null
        tls = {
          certificateArn = var.acm_certificate_arn != "" ? var.acm_certificate_arn : null
        }
      }
    }
    controllers = {
      externalDns = {
        roleArn = module.controllers.external_dns_role_arn
      }
      awsLoadBalancerController = {
        roleArn = module.controllers.aws_load_balancer_controller_role_arn
      }
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

output "dns_contract" {
  description = "Domain/DNS/TLS contract placeholders for Route53 + ACM provisioning."
  value = {
    ingress_domain_name       = var.ingress_domain_name != "" ? var.ingress_domain_name : null
    observability_domain_name = var.observability_domain_name != "" ? var.observability_domain_name : null
    route53_hosted_zone_id    = var.route53_hosted_zone_id != "" ? var.route53_hosted_zone_id : null
    acm_certificate_arn       = var.acm_certificate_arn != "" ? var.acm_certificate_arn : null
  }
}
