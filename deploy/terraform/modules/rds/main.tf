locals {
  db_identifier   = substr("${var.name_prefix}-postgres", 0, 63)
  subnet_grp_name = substr("${var.name_prefix}-db-subnet-group", 0, 255)
}

resource "aws_db_subnet_group" "this" {
  name       = local.subnet_grp_name
  subnet_ids = var.private_subnet_ids

  tags = merge(var.tags, {
    Name = local.subnet_grp_name
  })
}

resource "aws_security_group" "db" {
  name        = "${var.name_prefix}-db-sg"
  description = "Security group for PostgreSQL."
  vpc_id      = var.vpc_id

  ingress {
    description     = "PostgreSQL from application security group."
    from_port       = 5432
    to_port         = 5432
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
    Name = "${var.name_prefix}-db-sg"
  })
}

resource "aws_db_instance" "this" {
  identifier = local.db_identifier

  engine         = "postgres"
  engine_version = var.engine_version
  instance_class = var.instance_class

  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.master_username

  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.db.id]

  publicly_accessible     = false
  multi_az                = false
  backup_retention_period = var.backup_retention_period
  deletion_protection     = var.deletion_protection
  skip_final_snapshot     = var.skip_final_snapshot
  apply_immediately       = true

  tags = merge(var.tags, {
    Name = local.db_identifier
  })
}
