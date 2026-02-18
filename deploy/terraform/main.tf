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
