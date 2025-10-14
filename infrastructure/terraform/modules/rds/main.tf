# RDS Module for AI Nutritionist
# Provides highly available, secure, and scalable database infrastructure

locals {
  common_tags = merge(var.tags, {
    Module = "rds"
  })

  # Generate final snapshot identifier
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${var.identifier}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  
  # Database engine configurations
  engine_configs = {
    postgres = {
      engine         = "postgres"
      engine_version = var.postgres_version
      port           = 5432
      family         = "postgres${split(".", var.postgres_version)[0]}"
    }
    mysql = {
      engine         = "mysql"
      engine_version = var.mysql_version
      port           = 3306
      family         = "mysql${var.mysql_version}"
    }
  }

  engine_config = local.engine_configs[var.engine_type]
}

# KMS Key for RDS encryption
resource "aws_kms_key" "rds" {
  count = var.kms_key_id == null ? 1 : 0

  description             = "KMS key for RDS encryption - ${var.identifier}"
  deletion_window_in_days = var.kms_deletion_window
  enable_key_rotation     = true

  tags = merge(local.common_tags, {
    Name = "${var.identifier}-rds-kms-key"
    Type = "kms-key"
  })
}

resource "aws_kms_alias" "rds" {
  count = var.kms_key_id == null ? 1 : 0

  name          = "alias/${var.identifier}-rds"
  target_key_id = aws_kms_key.rds[0].key_id
}

# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "${var.identifier}-subnet-group"
  subnet_ids = var.subnet_ids

  tags = merge(local.common_tags, {
    Name = "${var.identifier}-subnet-group"
    Type = "db-subnet-group"
  })
}

# DB Parameter Group
resource "aws_db_parameter_group" "main" {
  count = var.create_parameter_group ? 1 : 0

  family = local.engine_config.family
  name   = "${var.identifier}-params"

  dynamic "parameter" {
    for_each = var.db_parameters
    content {
      name  = parameter.value.name
      value = parameter.value.value
    }
  }

  tags = merge(local.common_tags, {
    Name = "${var.identifier}-parameter-group"
    Type = "db-parameter-group"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Security Group for RDS
resource "aws_security_group" "rds" {
  name_prefix = "${var.identifier}-rds-"
  vpc_id      = var.vpc_id

  description = "Security group for RDS instance ${var.identifier}"

  # Database access from application subnets
  ingress {
    description = "Database access from application layer"
    from_port   = local.engine_config.port
    to_port     = local.engine_config.port
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  # Access from specific security groups (application layer)
  dynamic "ingress" {
    for_each = var.allowed_security_groups
    content {
      description     = "Database access from ${ingress.value}"
      from_port       = local.engine_config.port
      to_port         = local.engine_config.port
      protocol        = "tcp"
      security_groups = [ingress.value]
    }
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.identifier}-rds-sg"
    Type = "security-group"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# RDS Instance
resource "aws_db_instance" "main" {
  # Basic Configuration
  identifier        = var.identifier
  engine            = local.engine_config.engine
  engine_version    = local.engine_config.engine_version
  instance_class    = var.instance_class
  allocated_storage = var.allocated_storage
  storage_type      = var.storage_type
  storage_encrypted = var.storage_encrypted
  kms_key_id        = var.kms_key_id != null ? var.kms_key_id : (var.storage_encrypted ? aws_kms_key.rds[0].arn : null)

  # Database Configuration
  db_name  = var.database_name
  username = var.master_username
  password = var.master_password

  # Network Configuration
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = concat([aws_security_group.rds.id], var.additional_security_groups)
  port                   = local.engine_config.port
  publicly_accessible    = var.publicly_accessible

  # High Availability
  multi_az               = var.multi_az
  availability_zone      = var.multi_az ? null : var.availability_zone

  # Backup Configuration
  backup_retention_period = var.backup_retention_period
  backup_window          = var.backup_window
  copy_tags_to_snapshot  = true
  delete_automated_backups = var.delete_automated_backups

  # Maintenance Configuration
  maintenance_window         = var.maintenance_window
  auto_minor_version_upgrade = var.auto_minor_version_upgrade
  allow_major_version_upgrade = var.allow_major_version_upgrade

  # Parameter Group
  parameter_group_name = var.create_parameter_group ? aws_db_parameter_group.main[0].name : var.parameter_group_name

  # Monitoring
  monitoring_interval = var.monitoring_interval
  monitoring_role_arn = var.monitoring_interval > 0 ? aws_iam_role.monitoring[0].arn : null
  
  performance_insights_enabled          = var.performance_insights_enabled
  performance_insights_kms_key_id       = var.performance_insights_enabled ? (var.kms_key_id != null ? var.kms_key_id : aws_kms_key.rds[0].arn) : null
  performance_insights_retention_period = var.performance_insights_enabled ? var.performance_insights_retention_period : null

  # Logging
  enabled_cloudwatch_logs_exports = var.enabled_cloudwatch_logs_exports

  # Final Snapshot
  skip_final_snapshot       = var.skip_final_snapshot
  final_snapshot_identifier = local.final_snapshot_identifier

  # Deletion Protection
  deletion_protection = var.deletion_protection

  # Storage Autoscaling
  max_allocated_storage = var.max_allocated_storage

  tags = merge(local.common_tags, {
    Name = var.identifier
    Type = "rds-instance"
    Engine = local.engine_config.engine
  })

  lifecycle {
    ignore_changes = [
      password,
      final_snapshot_identifier
    ]
  }

  depends_on = [
    aws_db_subnet_group.main,
    aws_security_group.rds
  ]
}

# Read Replica (optional)
resource "aws_db_instance" "read_replica" {
  count = var.create_read_replica ? 1 : 0

  identifier              = "${var.identifier}-read-replica"
  replicate_source_db     = aws_db_instance.main.identifier
  instance_class          = var.read_replica_instance_class != null ? var.read_replica_instance_class : var.instance_class
  auto_minor_version_upgrade = var.auto_minor_version_upgrade
  
  # Network Configuration for Cross-AZ read replica
  availability_zone = var.read_replica_availability_zone
  publicly_accessible = false

  # Monitoring
  monitoring_interval = var.monitoring_interval
  monitoring_role_arn = var.monitoring_interval > 0 ? aws_iam_role.monitoring[0].arn : null

  performance_insights_enabled          = var.performance_insights_enabled
  performance_insights_kms_key_id       = var.performance_insights_enabled ? (var.kms_key_id != null ? var.kms_key_id : aws_kms_key.rds[0].arn) : null
  performance_insights_retention_period = var.performance_insights_enabled ? var.performance_insights_retention_period : null

  # Final Snapshot
  skip_final_snapshot       = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${var.identifier}-read-replica-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  # Deletion Protection
  deletion_protection = var.deletion_protection

  tags = merge(local.common_tags, {
    Name = "${var.identifier}-read-replica"
    Type = "rds-read-replica"
    Engine = local.engine_config.engine
  })

  lifecycle {
    ignore_changes = [
      final_snapshot_identifier
    ]
  }
}

# Enhanced Monitoring IAM Role
resource "aws_iam_role" "monitoring" {
  count = var.monitoring_interval > 0 ? 1 : 0

  name = "${var.identifier}-rds-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "monitoring" {
  count = var.monitoring_interval > 0 ? 1 : 0

  role       = aws_iam_role.monitoring[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# CloudWatch Log Groups for RDS logs
resource "aws_cloudwatch_log_group" "rds" {
  for_each = toset(var.enabled_cloudwatch_logs_exports)

  name              = "/aws/rds/instance/${var.identifier}/${each.value}"
  retention_in_days = var.log_retention_period

  tags = merge(local.common_tags, {
    Name = "${var.identifier}-${each.value}-logs"
    Type = "cloudwatch-log-group"
  })
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "database_cpu" {
  count = var.create_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.identifier}-database-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = var.cpu_alarm_threshold
  alarm_description   = "This metric monitors rds cpu utilization"
  alarm_actions       = var.alarm_actions

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "database_connections" {
  count = var.create_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.identifier}-database-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = var.connection_alarm_threshold
  alarm_description   = "This metric monitors rds database connections"
  alarm_actions       = var.alarm_actions

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "database_free_storage" {
  count = var.create_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.identifier}-database-free-storage"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = var.free_storage_alarm_threshold
  alarm_description   = "This metric monitors rds free storage space"
  alarm_actions       = var.alarm_actions

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = local.common_tags
}
