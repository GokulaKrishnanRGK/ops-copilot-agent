locals {
  ecr_repositories = {
    api         = "${var.name_prefix}/api"
    web         = "${var.name_prefix}/web"
    tool_server = "${var.name_prefix}/tool-server"
  }

  package_registry_url = null
}
