# ElastiCache Module for AI Nutritionist
# Provides Redis and Memcached caching infrastructure

locals {
  common_tags = merge(var.tags, {
    Module = "elasticache"
  })

  # Engine-specific configurations
  engine_configs = {
    redis = {
      engine                = "redis"
      port                  = 6379
      parameter_group_family = "redis${var.redis_version}"
      default_parameters = [
        {
          name  = "maxmemory-policy"
          value = "allkeys-lru"
        }
      ]
    }
    memcached = {
      engine                = "memcached"
      port                  = 11211
      parameter_group_family = "memcached${var.memcached_version}"
      default_parameters = []
    }
  }

  engine_config = local.engine_configs[var.engine]
  
  # Determine if we need a replication group (Redis cluster)
  is_redis_cluster = var.engine == "redis" && (var.num_cache_clusters > 1 || var.automatic_failover_enabled)
}

# KMS Key for ElastiCache encryption
resource "aws_kms_key" "elasticache" {
  count = var.at_rest_encryption_enabled && var.kms_key_id == null ? 1 : 0

  description             = "KMS key for ElastiCache encryption - ${var.cluster_id}"
  deletion_window_in_days = var.kms_deletion_window
  enable_key_rotation     = true

  tags = merge(local.common_tags, {
    Name = "${var.cluster_id}-elasticache-kms-key"
    Type = "kms-key"
  })
}

resource "aws_kms_alias" "elasticache" {
  count = var.at_rest_encryption_enabled && var.kms_key_id == null ? 1 : 0

  name          = "alias/${var.cluster_id}-elasticache"
  target_key_id = aws_kms_key.elasticache[0].key_id
}

# Subnet Group
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.cluster_id}-subnet-group"
  subnet_ids = var.subnet_ids

  tags = merge(local.common_tags, {
    Name = "${var.cluster_id}-subnet-group"
    Type = "elasticache-subnet-group"
  })
}

# Parameter Group
resource "aws_elasticache_parameter_group" "main" {
  count = var.create_parameter_group ? 1 : 0

  family = local.engine_config.parameter_group_family
  name   = "${var.cluster_id}-params"

  dynamic "parameter" {
    for_each = concat(local.engine_config.default_parameters, var.cache_parameters)
    content {
      name  = parameter.value.name
      value = parameter.value.value
    }
  }

  tags = merge(local.common_tags, {
    Name = "${var.cluster_id}-parameter-group"
    Type = "elasticache-parameter-group"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Security Group for ElastiCache
resource "aws_security_group" "elasticache" {
  name_prefix = "${var.cluster_id}-elasticache-"
  vpc_id      = var.vpc_id

  description = "Security group for ElastiCache cluster ${var.cluster_id}"

  # Cache access from application subnets
  ingress {
    description = "Cache access from application layer"
    from_port   = local.engine_config.port
    to_port     = local.engine_config.port
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  # Access from specific security groups (application layer)
  dynamic "ingress" {
    for_each = var.allowed_security_groups
    content {
      description     = "Cache access from ${ingress.value}"
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
    Name = "${var.cluster_id}-elasticache-sg"
    Type = "security-group"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Redis Replication Group (for Redis clusters)
resource "aws_elasticache_replication_group" "redis" {
  count = var.engine == "redis" && local.is_redis_cluster ? 1 : 0

  replication_group_id         = var.cluster_id
  description                  = "Redis replication group for ${var.cluster_id}"
  
  # Engine Configuration
  engine               = "redis"
  engine_version       = var.redis_version
  node_type            = var.node_type
  port                 = local.engine_config.port
  parameter_group_name = var.create_parameter_group ? aws_elasticache_parameter_group.main[0].name : var.parameter_group_name

  # Cluster Configuration
  num_cache_clusters         = var.num_cache_clusters
  automatic_failover_enabled = var.automatic_failover_enabled
  multi_az_enabled          = var.multi_az_enabled
  
  # Network Configuration
  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = concat([aws_security_group.elasticache.id], var.additional_security_groups)

  # Backup Configuration
  snapshot_retention_limit = var.snapshot_retention_limit
  snapshot_window         = var.snapshot_window
  final_snapshot_identifier = var.final_snapshot_identifier

  # Maintenance
  maintenance_window          = var.maintenance_window
  auto_minor_version_upgrade  = var.auto_minor_version_upgrade

  # Encryption
  at_rest_encryption_enabled  = var.at_rest_encryption_enabled
  transit_encryption_enabled  = var.transit_encryption_enabled
  kms_key_id                 = var.at_rest_encryption_enabled ? (var.kms_key_id != null ? var.kms_key_id : aws_kms_key.elasticache[0].arn) : null
  auth_token                 = var.transit_encryption_enabled ? var.auth_token : null

  # Logging
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.elasticache_slow_log[0].name
    destination_type = "cloudwatch-logs"
    log_format       = "text"
    log_type         = "slow-log"
  }

  tags = merge(local.common_tags, {
    Name = var.cluster_id
    Type = "elasticache-replication-group"
    Engine = "redis"
  })

  lifecycle {
    ignore_changes = [
      auth_token
    ]
  }

  depends_on = [
    aws_elasticache_subnet_group.main,
    aws_security_group.elasticache
  ]
}

# Single Redis Instance (for simple Redis deployments)
resource "aws_elasticache_cluster" "redis_single" {
  count = var.engine == "redis" && !local.is_redis_cluster ? 1 : 0

  cluster_id           = var.cluster_id
  engine               = "redis"
  engine_version       = var.redis_version
  node_type            = var.node_type
  port                 = local.engine_config.port
  num_cache_nodes      = 1
  parameter_group_name = var.create_parameter_group ? aws_elasticache_parameter_group.main[0].name : var.parameter_group_name
  
  # Network Configuration
  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = concat([aws_security_group.elasticache.id], var.additional_security_groups)
  availability_zone  = var.availability_zone

  # Backup Configuration
  snapshot_retention_limit = var.snapshot_retention_limit
  snapshot_window         = var.snapshot_window
  final_snapshot_identifier = var.final_snapshot_identifier

  # Maintenance
  maintenance_window         = var.maintenance_window
  auto_minor_version_upgrade = var.auto_minor_version_upgrade

  tags = merge(local.common_tags, {
    Name = var.cluster_id
    Type = "elasticache-cluster"
    Engine = "redis"
  })

  depends_on = [
    aws_elasticache_subnet_group.main,
    aws_security_group.elasticache
  ]
}

# Memcached Cluster
resource "aws_elasticache_cluster" "memcached" {
  count = var.engine == "memcached" ? 1 : 0

  cluster_id           = var.cluster_id
  engine               = "memcached"
  engine_version       = var.memcached_version
  node_type            = var.node_type
  port                 = local.engine_config.port
  num_cache_nodes      = var.num_cache_nodes
  parameter_group_name = var.create_parameter_group ? aws_elasticache_parameter_group.main[0].name : var.parameter_group_name
  
  # Network Configuration
  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = concat([aws_security_group.elasticache.id], var.additional_security_groups)
  az_mode            = var.num_cache_nodes > 1 ? "cross-az" : "single-az"

  # Maintenance
  maintenance_window         = var.maintenance_window
  auto_minor_version_upgrade = var.auto_minor_version_upgrade

  tags = merge(local.common_tags, {
    Name = var.cluster_id
    Type = "elasticache-cluster"
    Engine = "memcached"
  })

  depends_on = [
    aws_elasticache_subnet_group.main,
    aws_security_group.elasticache
  ]
}

# CloudWatch Log Groups for Redis logs
resource "aws_cloudwatch_log_group" "elasticache_slow_log" {
  count = var.engine == "redis" && var.enable_logging ? 1 : 0

  name              = "/aws/elasticache/redis/${var.cluster_id}/slow-log"
  retention_in_days = var.log_retention_period

  tags = merge(local.common_tags, {
    Name = "${var.cluster_id}-slow-log"
    Type = "cloudwatch-log-group"
  })
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "cache_cpu" {
  count = var.create_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.cluster_id}-cache-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = var.cpu_alarm_threshold
  alarm_description   = "This metric monitors elasticache cpu utilization"
  alarm_actions       = var.alarm_actions

  dimensions = var.engine == "redis" && local.is_redis_cluster ? {
    ReplicationGroupId = aws_elasticache_replication_group.redis[0].id
  } : {
    CacheClusterId = var.engine == "redis" ? aws_elasticache_cluster.redis_single[0].id : aws_elasticache_cluster.memcached[0].id
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "cache_memory" {
  count = var.create_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.cluster_id}-cache-memory-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = var.engine == "redis" ? "DatabaseMemoryUsagePercentage" : "SwapUsage"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = var.memory_alarm_threshold
  alarm_description   = "This metric monitors elasticache memory utilization"
  alarm_actions       = var.alarm_actions

  dimensions = var.engine == "redis" && local.is_redis_cluster ? {
    ReplicationGroupId = aws_elasticache_replication_group.redis[0].id
  } : {
    CacheClusterId = var.engine == "redis" ? aws_elasticache_cluster.redis_single[0].id : aws_elasticache_cluster.memcached[0].id
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "cache_evictions" {
  count = var.create_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.cluster_id}-cache-evictions"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Evictions"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = var.evictions_alarm_threshold
  alarm_description   = "This metric monitors elasticache evictions"
  alarm_actions       = var.alarm_actions

  dimensions = var.engine == "redis" && local.is_redis_cluster ? {
    ReplicationGroupId = aws_elasticache_replication_group.redis[0].id
  } : {
    CacheClusterId = var.engine == "redis" ? aws_elasticache_cluster.redis_single[0].id : aws_elasticache_cluster.memcached[0].id
  }

  tags = local.common_tags
}
