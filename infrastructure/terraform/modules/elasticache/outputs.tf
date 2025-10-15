# Outputs for ElastiCache Module

# Redis Replication Group Outputs
output "replication_group_id" {
  description = "The ID of the ElastiCache Replication Group"
  value       = var.engine == "redis" && (var.num_cache_clusters > 1 || var.automatic_failover_enabled) ? aws_elasticache_replication_group.redis[0].id : null
}

output "replication_group_arn" {
  description = "The Amazon Resource Name (ARN) of the created ElastiCache Replication Group"
  value       = var.engine == "redis" && (var.num_cache_clusters > 1 || var.automatic_failover_enabled) ? aws_elasticache_replication_group.redis[0].arn : null
}

output "primary_endpoint_address" {
  description = "The address of the endpoint for the primary node in the replication group"
  value       = var.engine == "redis" && (var.num_cache_clusters > 1 || var.automatic_failover_enabled) ? aws_elasticache_replication_group.redis[0].primary_endpoint_address : null
}

output "reader_endpoint_address" {
  description = "The address of the endpoint for the reader node in the replication group"
  value       = var.engine == "redis" && (var.num_cache_clusters > 1 || var.automatic_failover_enabled) ? aws_elasticache_replication_group.redis[0].reader_endpoint_address : null
}

output "configuration_endpoint_address" {
  description = "The configuration endpoint address to allow host discovery"
  value       = var.engine == "redis" && (var.num_cache_clusters > 1 || var.automatic_failover_enabled) ? aws_elasticache_replication_group.redis[0].configuration_endpoint_address : null
}

# Single Redis Instance Outputs
output "redis_cache_nodes" {
  description = "List of cache nodes for single Redis instance"
  value       = var.engine == "redis" && !(var.num_cache_clusters > 1 || var.automatic_failover_enabled) ? aws_elasticache_cluster.redis_single[0].cache_nodes : null
}

output "redis_cluster_address" {
  description = "The DNS name of the cache cluster without the port appended (Redis single instance)"
  value       = var.engine == "redis" && !(var.num_cache_clusters > 1 || var.automatic_failover_enabled) ? aws_elasticache_cluster.redis_single[0].cluster_address : null
}

# Memcached Cluster Outputs
output "memcached_cluster_id" {
  description = "The cluster ID of the Memcached cluster"
  value       = var.engine == "memcached" ? aws_elasticache_cluster.memcached[0].cluster_id : null
}

output "memcached_cluster_address" {
  description = "The DNS name of the cache cluster without the port appended (Memcached)"
  value       = var.engine == "memcached" ? aws_elasticache_cluster.memcached[0].cluster_address : null
}

output "memcached_cache_nodes" {
  description = "List of cache nodes for Memcached cluster"
  value       = var.engine == "memcached" ? aws_elasticache_cluster.memcached[0].cache_nodes : null
}

output "memcached_configuration_endpoint" {
  description = "The configuration endpoint to allow host discovery (Memcached)"
  value       = var.engine == "memcached" ? aws_elasticache_cluster.memcached[0].configuration_endpoint : null
}

# Common Outputs
output "port" {
  description = "The port number on which each of the cache nodes will accept connections"
  value = var.engine == "redis" ? (
    (var.num_cache_clusters > 1 || var.automatic_failover_enabled) ? 
    aws_elasticache_replication_group.redis[0].port : 
    aws_elasticache_cluster.redis_single[0].port
  ) : aws_elasticache_cluster.memcached[0].port
}

output "engine_version" {
  description = "The running version of the cache engine"
  value = var.engine == "redis" ? (
    (var.num_cache_clusters > 1 || var.automatic_failover_enabled) ? 
    aws_elasticache_replication_group.redis[0].engine_version : 
    aws_elasticache_cluster.redis_single[0].engine_version
  ) : aws_elasticache_cluster.memcached[0].engine_version
}

# Security Group
output "security_group_id" {
  description = "The ID of the security group"
  value       = aws_security_group.elasticache.id
}

output "security_group_arn" {
  description = "The ARN of the security group"
  value       = aws_security_group.elasticache.arn
}

# Subnet Group
output "subnet_group_name" {
  description = "The name of the cache subnet group"
  value       = aws_elasticache_subnet_group.main.name
}

# Parameter Group
output "parameter_group_id" {
  description = "The cache parameter group id"
  value       = var.create_parameter_group ? aws_elasticache_parameter_group.main[0].id : null
}

# KMS Key
output "kms_key_id" {
  description = "The globally unique identifier for the key"
  value       = var.kms_key_id != null ? var.kms_key_id : (var.at_rest_encryption_enabled ? aws_kms_key.elasticache[0].key_id : null)
}

output "kms_key_arn" {
  description = "The Amazon Resource Name (ARN) of the key"
  value       = var.kms_key_id != null ? var.kms_key_id : (var.at_rest_encryption_enabled ? aws_kms_key.elasticache[0].arn : null)
}

# CloudWatch Log Groups
output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group for slow logs"
  value       = var.engine == "redis" && var.enable_logging ? aws_cloudwatch_log_group.elasticache_slow_log[0].name : null
}

# CloudWatch Alarms
output "cloudwatch_alarm_ids" {
  description = "List of CloudWatch alarm IDs"
  value = var.create_cloudwatch_alarms ? [
    aws_cloudwatch_metric_alarm.cache_cpu[0].id,
    aws_cloudwatch_metric_alarm.cache_memory[0].id,
    aws_cloudwatch_metric_alarm.cache_evictions[0].id
  ] : []
}

# Connection Information
output "connection_info" {
  description = "Cache connection information"
  value = {
    engine = var.engine
    port   = var.engine == "redis" ? (
      (var.num_cache_clusters > 1 || var.automatic_failover_enabled) ? 
      aws_elasticache_replication_group.redis[0].port : 
      aws_elasticache_cluster.redis_single[0].port
    ) : aws_elasticache_cluster.memcached[0].port
    
    primary_endpoint = var.engine == "redis" ? (
      (var.num_cache_clusters > 1 || var.automatic_failover_enabled) ? 
      aws_elasticache_replication_group.redis[0].primary_endpoint_address : 
      aws_elasticache_cluster.redis_single[0].cluster_address
    ) : aws_elasticache_cluster.memcached[0].cluster_address
    
    configuration_endpoint = var.engine == "memcached" ? aws_elasticache_cluster.memcached[0].configuration_endpoint : null
  }
}

# Cluster Information
output "cluster_enabled" {
  description = "Whether Redis clustering is enabled"
  value       = var.engine == "redis" && (var.num_cache_clusters > 1 || var.automatic_failover_enabled)
}

output "multi_az" {
  description = "Whether Multi-AZ is enabled"
  value       = var.engine == "redis" ? var.multi_az_enabled : (var.num_cache_nodes > 1)
}

# Resource Tags
output "tags" {
  description = "A map of tags assigned to the resource"
  value = var.engine == "redis" ? (
    (var.num_cache_clusters > 1 || var.automatic_failover_enabled) ? 
    aws_elasticache_replication_group.redis[0].tags_all : 
    aws_elasticache_cluster.redis_single[0].tags_all
  ) : aws_elasticache_cluster.memcached[0].tags_all
}
