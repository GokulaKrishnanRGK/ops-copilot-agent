module "network" {
  source = "./modules/network"

  name_prefix = local.name_prefix
  tags        = local.common_tags
  vpc_cidr    = var.network_vpc_cidr
  az_count    = var.network_az_count
}

module "rds" {
  source = "./modules/rds"

  name_prefix          = local.name_prefix
  tags                 = local.common_tags
  vpc_id               = module.network.vpc_id
  vpc_cidr             = var.network_vpc_cidr
  private_subnet_ids   = module.network.private_subnet_ids
  security_group_id    = module.network.app_security_group_id
  database_secret_name = "${local.name_prefix}-db"
}

module "opensearch" {
  source = "./modules/opensearch"

  name_prefix        = local.name_prefix
  tags               = local.common_tags
  vpc_id             = module.network.vpc_id
  vpc_cidr           = var.network_vpc_cidr
  private_subnet_ids = module.network.private_subnet_ids
  security_group_id  = module.network.app_security_group_id
}

module "artifacts" {
  source = "./modules/artifacts"

  name_prefix                    = local.name_prefix
  tags                           = local.common_tags
  create_python_package_registry = var.artifacts_create_python_package_registry
  ecr_scan_on_push               = var.artifacts_ecr_scan_on_push
}

module "eks" {
  source = "./modules/eks"

  name_prefix = local.name_prefix
  tags        = local.common_tags

  public_subnet_ids  = module.network.public_subnet_ids
  private_subnet_ids = module.network.private_subnet_ids

  cluster_name       = var.eks_cluster_name != "" ? var.eks_cluster_name : "${local.name_prefix}-eks"
  kubernetes_version = var.eks_kubernetes_version

  node_instance_types = var.eks_node_instance_types
  node_desired_size   = var.eks_node_desired_size
  node_min_size       = var.eks_node_min_size
  node_max_size       = var.eks_node_max_size
  node_disk_size      = var.eks_node_disk_size

  endpoint_public_access  = var.eks_endpoint_public_access
  endpoint_private_access = var.eks_endpoint_private_access
  public_access_cidrs     = var.eks_public_access_cidrs
}

module "controllers" {
  source = "./modules/controllers"

  create = var.controllers_create_irsa_roles

  name_prefix = local.name_prefix
  tags        = local.common_tags

  oidc_provider_arn = module.eks.oidc_provider_arn
  oidc_provider_url = module.eks.oidc_issuer_url

  external_dns_namespace            = var.external_dns_namespace
  external_dns_service_account_name = var.external_dns_service_account_name

  aws_load_balancer_controller_namespace            = var.aws_load_balancer_controller_namespace
  aws_load_balancer_controller_service_account_name = var.aws_load_balancer_controller_service_account_name
}
