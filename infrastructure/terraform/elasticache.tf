# ElastiCache Redis for Enhanced Performance and Caching
# Best Practice: Reduces API calls to Bedrock and improves response times

# ElastiCache Subnet Group
resource "aws_elasticache_subnet_group" "main" {
  count = var.enable_elasticache ? 1 : 0
  
  name       = "${var.project_name}-cache-subnet-group-${var.environment}"
  subnet_ids = var.enable_vpc ? aws_subnet.private[*].id : data.aws_subnets.default[0].ids

  tags = merge(
    {
      Name = "${var.project_name}-cache-subnet-group-${var.environment}"
    },
    var.additional_tags
  )
}

# ElastiCache Parameter Group for Redis
resource "aws_elasticache_parameter_group" "redis" {
  count = var.enable_elasticache ? 1 : 0
  
  family = "redis7.x"
  name   = "${var.project_name}-redis-params-${var.environment}"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  parameter {
    name  = "timeout"
    value = "300"
  }

  tags = merge(
    {
      Name = "${var.project_name}-redis-params-${var.environment}"
    },
    var.additional_tags
  )
}

# Security Group for ElastiCache
resource "aws_security_group" "elasticache" {
  count = var.enable_elasticache ? 1 : 0
  
  name_prefix = "${var.project_name}-elasticache-${var.environment}-"
  vpc_id      = var.enable_vpc ? aws_vpc.main[0].id : data.aws_vpc.default[0].id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = var.enable_vpc ? [aws_security_group.lambda_enhanced[0].id] : [aws_security_group.lambda[0].id]
    description     = "Redis access from Lambda functions"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = merge(
    {
      Name = "${var.project_name}-elasticache-sg-${var.environment}"
    },
    var.additional_tags
  )

  lifecycle {
    create_before_destroy = true
  }
}

# ElastiCache Redis Replication Group
resource "aws_elasticache_replication_group" "redis" {
  count = var.enable_elasticache ? 1 : 0
  
  replication_group_id         = "${var.project_name}-redis-${var.environment}"
  description                  = "Redis cluster for AI Nutritionist caching"
  
  # Redis Configuration
  port                         = 6379
  parameter_group_name         = aws_elasticache_parameter_group.redis[0].name
  node_type                    = var.elasticache_node_type
  num_cache_clusters           = var.elasticache_num_nodes
  
  # Engine Configuration
  engine_version               = "7.0"
  
  # Security
  at_rest_encryption_enabled   = true
  transit_encryption_enabled   = true
  auth_token                   = var.elasticache_auth_token
  kms_key_id                   = aws_kms_key.elasticache[0].arn
  
  # Networking
  subnet_group_name            = aws_elasticache_subnet_group.main[0].name
  security_group_ids           = [aws_security_group.elasticache[0].id]
  
  # Maintenance
  maintenance_window           = var.elasticache_maintenance_window
  snapshot_retention_limit     = var.elasticache_snapshot_retention
  snapshot_window              = var.elasticache_snapshot_window
  
  # Backup
  automatic_failover_enabled   = var.elasticache_num_nodes > 1
  multi_az_enabled            = var.elasticache_num_nodes > 1 && var.environment == "prod"
  
  # Notifications
  notification_topic_arn       = var.enable_sns_alerts ? aws_sns_topic.alerts[0].arn : null

  tags = merge(
    {
      Name = "${var.project_name}-redis-${var.environment}"
      Type = "Cache"
    },
    var.additional_tags
  )

  lifecycle {
    ignore_changes = [num_cache_clusters]
  }
}

# KMS Key for ElastiCache Encryption
resource "aws_kms_key" "elasticache" {
  count = var.enable_elasticache ? 1 : 0
  
  description             = "KMS key for ElastiCache encryption - ${var.project_name} ${var.environment}"
  deletion_window_in_days = var.environment == "prod" ? 30 : 7
  enable_key_rotation     = true

  tags = merge(
    {
      Name    = "${var.project_name}-elasticache-key-${var.environment}"
      Purpose = "ElastiCache encryption"
    },
    var.additional_tags
  )
}

resource "aws_kms_alias" "elasticache" {
  count = var.enable_elasticache ? 1 : 0
  
  name          = "alias/${var.project_name}-elasticache-${var.environment}"
  target_key_id = aws_kms_key.elasticache[0].key_id
}

# CloudWatch Alarms for ElastiCache
resource "aws_cloudwatch_metric_alarm" "elasticache_cpu" {
  count = var.enable_elasticache && var.enable_monitoring ? 1 : 0
  
  alarm_name          = "${var.project_name}-elasticache-cpu-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ElastiCache CPU utilization"
  alarm_actions       = var.enable_sns_alerts ? [aws_sns_topic.alerts[0].arn] : []

  dimensions = {
    CacheClusterId = "${aws_elasticache_replication_group.redis[0].replication_group_id}-001"
  }

  tags = merge(
    {
      Name = "${var.project_name}-elasticache-cpu-alarm-${var.environment}"
    },
    var.additional_tags
  )
}

resource "aws_cloudwatch_metric_alarm" "elasticache_memory" {
  count = var.enable_elasticache && var.enable_monitoring ? 1 : 0
  
  alarm_name          = "${var.project_name}-elasticache-memory-${var.environment}"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "FreeableMemory"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = "100000000" # 100MB in bytes
  alarm_description   = "This metric monitors ElastiCache freeable memory"
  alarm_actions       = var.enable_sns_alerts ? [aws_sns_topic.alerts[0].arn] : []

  dimensions = {
    CacheClusterId = "${aws_elasticache_replication_group.redis[0].replication_group_id}-001"
  }

  tags = merge(
    {
      Name = "${var.project_name}-elasticache-memory-alarm-${var.environment}"
    },
    var.additional_tags
  )
}

# ElastiCache User for Application Access
resource "aws_elasticache_user" "app_user" {
  count = var.enable_elasticache ? 1 : 0
  
  user_id       = "${var.project_name}-app-user-${var.environment}"
  user_name     = "app-user"
  access_string = "on ~* +@all"
  engine        = "REDIS"
  passwords     = [var.elasticache_auth_token]

  tags = merge(
    {
      Name = "${var.project_name}-app-user-${var.environment}"
    },
    var.additional_tags
  )
}

# ElastiCache User Group
resource "aws_elasticache_user_group" "app_group" {
  count = var.enable_elasticache ? 1 : 0
  
  engine          = "REDIS"
  user_group_id   = "${var.project_name}-app-group-${var.environment}"
  user_ids        = [aws_elasticache_user.app_user[0].user_id]

  tags = merge(
    {
      Name = "${var.project_name}-app-group-${var.environment}"
    },
    var.additional_tags
  )
}

# Data sources for default VPC/subnets when VPC is not enabled
data "aws_vpc" "default" {
  count = var.enable_elasticache && !var.enable_vpc ? 1 : 0
  
  default = true
}

data "aws_subnets" "default" {
  count = var.enable_elasticache && !var.enable_vpc ? 1 : 0
  
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default[0].id]
  }
}

# SSM Parameters for ElastiCache Configuration
resource "aws_ssm_parameter" "elasticache_endpoint" {
  count = var.enable_elasticache ? 1 : 0
  
  name  = "/${var.project_name}/${var.environment}/elasticache/endpoint"
  type  = "String"
  value = aws_elasticache_replication_group.redis[0].configuration_endpoint_address

  tags = merge(
    {
      Name = "${var.project_name}-elasticache-endpoint-${var.environment}"
    },
    var.additional_tags
  )
}

resource "aws_ssm_parameter" "elasticache_port" {
  count = var.enable_elasticache ? 1 : 0
  
  name  = "/${var.project_name}/${var.environment}/elasticache/port"
  type  = "String"
  value = tostring(aws_elasticache_replication_group.redis[0].port)

  tags = merge(
    {
      Name = "${var.project_name}-elasticache-port-${var.environment}"
    },
    var.additional_tags
  )
}
