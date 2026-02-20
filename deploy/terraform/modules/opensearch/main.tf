data "aws_caller_identity" "current" {}

resource "random_password" "master" {
  length  = 24
  special = true
}

locals {
  domain_name          = substr("${var.name_prefix}-os", 0, 28)
  endpoint             = aws_opensearch_domain.this.endpoint
  username_secret_name = "${var.name_prefix}-opensearch-username"
  password_secret_name = "${var.name_prefix}-opensearch-password"
}

resource "aws_security_group" "opensearch" {
  name        = "${var.name_prefix}-opensearch-sg"
  description = "Security group for OpenSearch domain access."
  vpc_id      = var.vpc_id

  ingress {
    description     = "HTTPS from application security group."
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [var.security_group_id]
  }

  egress {
    description = "Allow DNS UDP inside VPC."
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "Allow DNS TCP inside VPC."
    from_port   = 53
    to_port     = 53
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-opensearch-sg"
  })
}

resource "aws_opensearch_domain" "this" {
  domain_name    = local.domain_name
  engine_version = var.engine_version

  cluster_config {
    instance_type  = var.instance_type
    instance_count = var.instance_count
  }

  ebs_options {
    ebs_enabled = true
    volume_type = "gp3"
    volume_size = var.volume_size
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  advanced_security_options {
    enabled                        = true
    internal_user_database_enabled = true
    master_user_options {
      master_user_name     = var.master_username
      master_user_password = random_password.master.result
    }
  }

  encrypt_at_rest {
    enabled = true
  }

  node_to_node_encryption {
    enabled = true
  }

  vpc_options {
    subnet_ids         = [var.private_subnet_ids[0]]
    security_group_ids = [aws_security_group.opensearch.id]
  }

  access_policies = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = data.aws_caller_identity.current.arn
        }
        Action   = "es:*"
        Resource = "arn:aws:es:*:*:domain/${local.domain_name}/*"
      }
    ]
  })

  tags = merge(var.tags, {
    Name = local.domain_name
  })
}

resource "aws_secretsmanager_secret" "username" {
  name                    = local.username_secret_name
  recovery_window_in_days = 0

  tags = merge(var.tags, {
    Name = local.username_secret_name
  })
}

resource "aws_secretsmanager_secret_version" "username" {
  secret_id     = aws_secretsmanager_secret.username.id
  secret_string = var.master_username
}

resource "aws_secretsmanager_secret" "password" {
  name                    = local.password_secret_name
  recovery_window_in_days = 0

  tags = merge(var.tags, {
    Name = local.password_secret_name
  })
}

resource "aws_secretsmanager_secret_version" "password" {
  secret_id     = aws_secretsmanager_secret.password.id
  secret_string = random_password.master.result
}
