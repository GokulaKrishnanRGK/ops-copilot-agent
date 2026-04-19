resource "random_password" "public_key_suffix" {
  length  = 32
  special = false
}

resource "random_password" "secret_key_suffix" {
  length  = 32
  special = false
}

locals {
  secret_name = "${var.name_prefix}-langfuse"
  public_key  = "pk-lf-${lower(random_password.public_key_suffix.result)}"
  secret_key  = "sk-lf-${lower(random_password.secret_key_suffix.result)}"
}

resource "aws_secretsmanager_secret" "langfuse" {
  name                    = local.secret_name
  recovery_window_in_days = 0

  tags = merge(var.tags, {
    Name = local.secret_name
  })
}

resource "aws_secretsmanager_secret_version" "langfuse" {
  secret_id = aws_secretsmanager_secret.langfuse.id
  secret_string = jsonencode({
    LANGFUSE_PUBLIC_KEY = local.public_key
    LANGFUSE_SECRET_KEY = local.secret_key
  })
}
