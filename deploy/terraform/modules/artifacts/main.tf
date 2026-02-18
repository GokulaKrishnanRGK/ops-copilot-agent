locals {
  ecr_repositories = {
    api         = "${var.name_prefix}/api"
    web         = "${var.name_prefix}/web"
    tool_server = "${var.name_prefix}/tool-server"
  }

  codeartifact_domain = var.codeartifact_domain_name != "" ? var.codeartifact_domain_name : "${var.name_prefix}-packages"
}

resource "aws_ecr_repository" "service" {
  for_each = local.ecr_repositories

  name                 = each.value
  image_tag_mutability = var.ecr_image_tag_mutability

  image_scanning_configuration {
    scan_on_push = var.ecr_scan_on_push
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = merge(var.tags, {
    Name    = each.value
    Service = each.key
  })
}

resource "aws_codeartifact_domain" "python" {
  count = var.create_python_package_registry ? 1 : 0

  domain = local.codeartifact_domain

  tags = merge(var.tags, {
    Name = local.codeartifact_domain
  })
}

resource "aws_codeartifact_repository" "python" {
  count = var.create_python_package_registry ? 1 : 0

  domain     = aws_codeartifact_domain.python[0].domain
  repository = var.codeartifact_repository_name

  external_connections {
    external_connection_name = "public:pypi"
  }

  tags = merge(var.tags, {
    Name = var.codeartifact_repository_name
  })
}

data "aws_codeartifact_repository_endpoint" "python_pypi" {
  count = var.create_python_package_registry ? 1 : 0

  domain     = aws_codeartifact_domain.python[0].domain
  repository = aws_codeartifact_repository.python[0].repository
  format     = "pypi"
}

locals {
  package_registry_url = var.create_python_package_registry ? data.aws_codeartifact_repository_endpoint.python_pypi[0].repository_endpoint : null
}
