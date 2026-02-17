locals {
  endpoint             = null
  username_secret_name = "${var.name_prefix}-opensearch-username"
  password_secret_name = "${var.name_prefix}-opensearch-password"
}
