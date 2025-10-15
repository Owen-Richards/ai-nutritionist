# Outputs for RDS Module

output "db_instance_id" {
  description = "The RDS instance ID"
  value       = aws_db_instance.main.id
}

output "db_instance_identifier" {
  description = "The RDS instance identifier"
  value       = aws_db_instance.main.identifier
}

output "db_instance_arn" {
  description = "The ARN of the RDS instance"
  value       = aws_db_instance.main.arn
}

output "db_instance_endpoint" {
  description = "The connection endpoint"
  value       = aws_db_instance.main.endpoint
}

output "db_instance_hosted_zone_id" {
  description = "The canonical hosted zone ID of the DB instance"
  value       = aws_db_instance.main.hosted_zone_id
}

output "db_instance_port" {
  description = "The database port"
  value       = aws_db_instance.main.port
}

output "db_instance_engine" {
  description = "The database engine"
  value       = aws_db_instance.main.engine
}

output "db_instance_engine_version" {
  description = "The running version of the database"
  value       = aws_db_instance.main.engine_version
}

output "db_instance_status" {
  description = "The RDS instance status"
  value       = aws_db_instance.main.status
}

output "db_instance_username" {
  description = "The master username for the database"
  value       = aws_db_instance.main.username
  sensitive   = true
}

output "db_instance_database_name" {
  description = "The database name"
  value       = aws_db_instance.main.db_name
}

# Read Replica Outputs
output "read_replica_id" {
  description = "The read replica instance ID"
  value       = var.create_read_replica ? aws_db_instance.read_replica[0].id : null
}

output "read_replica_identifier" {
  description = "The read replica instance identifier"
  value       = var.create_read_replica ? aws_db_instance.read_replica[0].identifier : null
}

output "read_replica_arn" {
  description = "The ARN of the read replica"
  value       = var.create_read_replica ? aws_db_instance.read_replica[0].arn : null
}

output "read_replica_endpoint" {
  description = "The read replica connection endpoint"
  value       = var.create_read_replica ? aws_db_instance.read_replica[0].endpoint : null
}

# Security Group
output "security_group_id" {
  description = "The ID of the security group"
  value       = aws_security_group.rds.id
}

output "security_group_arn" {
  description = "The ARN of the security group"
  value       = aws_security_group.rds.arn
}

# Subnet Group
output "db_subnet_group_id" {
  description = "The db subnet group name"
  value       = aws_db_subnet_group.main.id
}

output "db_subnet_group_arn" {
  description = "The ARN of the db subnet group"
  value       = aws_db_subnet_group.main.arn
}

# Parameter Group
output "db_parameter_group_id" {
  description = "The db parameter group id"
  value       = var.create_parameter_group ? aws_db_parameter_group.main[0].id : null
}

output "db_parameter_group_arn" {
  description = "The ARN of the db parameter group"
  value       = var.create_parameter_group ? aws_db_parameter_group.main[0].arn : null
}

# KMS Key
output "kms_key_id" {
  description = "The globally unique identifier for the key"
  value       = var.kms_key_id != null ? var.kms_key_id : (var.storage_encrypted ? aws_kms_key.rds[0].key_id : null)
}

output "kms_key_arn" {
  description = "The Amazon Resource Name (ARN) of the key"
  value       = var.kms_key_id != null ? var.kms_key_id : (var.storage_encrypted ? aws_kms_key.rds[0].arn : null)
}

# Monitoring
output "enhanced_monitoring_iam_role_arn" {
  description = "The Amazon Resource Name (ARN) specifying the monitoring role"
  value       = var.monitoring_interval > 0 ? aws_iam_role.monitoring[0].arn : null
}

# CloudWatch Log Groups
output "cloudwatch_log_group_names" {
  description = "Map of CloudWatch log group names"
  value = {
    for log_type in var.enabled_cloudwatch_logs_exports :
    log_type => aws_cloudwatch_log_group.rds[log_type].name
  }
}

# CloudWatch Alarms
output "cloudwatch_alarm_ids" {
  description = "List of CloudWatch alarm IDs"
  value = var.create_cloudwatch_alarms ? [
    aws_cloudwatch_metric_alarm.database_cpu[0].id,
    aws_cloudwatch_metric_alarm.database_connections[0].id,
    aws_cloudwatch_metric_alarm.database_free_storage[0].id
  ] : []
}

# Connection Information
output "connection_info" {
  description = "Database connection information"
  value = {
    endpoint = aws_db_instance.main.endpoint
    port     = aws_db_instance.main.port
    database = aws_db_instance.main.db_name
    username = aws_db_instance.main.username
  }
  sensitive = true
}

# Multi-AZ Information
output "multi_az" {
  description = "If the RDS instance is multi-AZ enabled"
  value       = aws_db_instance.main.multi_az
}

output "availability_zone" {
  description = "The availability zone of the instance"
  value       = aws_db_instance.main.availability_zone
}

# Backup Information
output "backup_retention_period" {
  description = "The backup retention period"
  value       = aws_db_instance.main.backup_retention_period
}

output "backup_window" {
  description = "The backup window"
  value       = aws_db_instance.main.backup_window
}

output "maintenance_window" {
  description = "The maintenance window"
  value       = aws_db_instance.main.maintenance_window
}

# Resource Tags
output "tags" {
  description = "A map of tags assigned to the resource"
  value       = aws_db_instance.main.tags_all
}
