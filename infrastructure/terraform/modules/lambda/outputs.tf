# Outputs for Lambda Module

# Function Information
output "function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.main.function_name
}

output "function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.main.arn
}

output "function_qualified_arn" {
  description = "Qualified ARN of the Lambda function"
  value       = aws_lambda_function.main.qualified_arn
}

output "function_invoke_arn" {
  description = "Invoke ARN of the Lambda function"
  value       = aws_lambda_function.main.invoke_arn
}

output "function_version" {
  description = "Latest published version of the Lambda function"
  value       = aws_lambda_function.main.version
}

output "function_last_modified" {
  description = "Date the function was last modified"
  value       = aws_lambda_function.main.last_modified
}

output "function_source_code_hash" {
  description = "Base64-encoded representation of raw SHA-256 sum of the zip file"
  value       = aws_lambda_function.main.source_code_hash
}

output "function_source_code_size" {
  description = "Size in bytes of the function .zip file"
  value       = aws_lambda_function.main.source_code_size
}

# Function URL
output "function_url" {
  description = "Function URL of the Lambda function"
  value       = var.create_function_url ? aws_lambda_function_url.main[0].function_url : null
}

output "function_url_creation_time" {
  description = "Creation time of the function URL"
  value       = var.create_function_url ? aws_lambda_function_url.main[0].creation_time : null
}

# Alias Information
output "alias_arn" {
  description = "ARN of the Lambda alias"
  value       = var.create_alias ? aws_lambda_alias.main[0].arn : null
}

output "alias_invoke_arn" {
  description = "Invoke ARN of the Lambda alias"
  value       = var.create_alias ? aws_lambda_alias.main[0].invoke_arn : null
}

output "alias_name" {
  description = "Name of the Lambda alias"
  value       = var.create_alias ? aws_lambda_alias.main[0].name : null
}

# IAM Role
output "execution_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_execution.arn
}

output "execution_role_name" {
  description = "Name of the Lambda execution role"
  value       = aws_iam_role.lambda_execution.name
}

# Security Group
output "security_group_id" {
  description = "ID of the Lambda security group"
  value       = var.vpc_config != null && var.create_security_group ? aws_security_group.lambda[0].id : null
}

output "security_group_arn" {
  description = "ARN of the Lambda security group"
  value       = var.vpc_config != null && var.create_security_group ? aws_security_group.lambda[0].arn : null
}

# KMS Key
output "kms_key_id" {
  description = "ID of the KMS key used for encryption"
  value       = var.kms_key_arn != null ? var.kms_key_arn : (var.environment_variables != {} ? aws_kms_key.lambda[0].key_id : null)
}

output "kms_key_arn" {
  description = "ARN of the KMS key used for encryption"
  value       = var.kms_key_arn != null ? var.kms_key_arn : (var.environment_variables != {} ? aws_kms_key.lambda[0].arn : null)
}

# CloudWatch Log Group
output "log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.lambda.name
}

output "log_group_arn" {
  description = "ARN of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.lambda.arn
}

# CloudWatch Alarms
output "cloudwatch_alarm_ids" {
  description = "List of CloudWatch alarm IDs"
  value = var.create_cloudwatch_alarms ? [
    aws_cloudwatch_metric_alarm.lambda_errors[0].id,
    aws_cloudwatch_metric_alarm.lambda_duration[0].id,
    aws_cloudwatch_metric_alarm.lambda_throttles[0].id
  ] : []
}

# Function Configuration
output "runtime" {
  description = "Runtime of the Lambda function"
  value       = aws_lambda_function.main.runtime
}

output "handler" {
  description = "Handler of the Lambda function"
  value       = aws_lambda_function.main.handler
}

output "memory_size" {
  description = "Memory size of the Lambda function"
  value       = aws_lambda_function.main.memory_size
}

output "timeout" {
  description = "Timeout of the Lambda function"
  value       = aws_lambda_function.main.timeout
}

output "package_type" {
  description = "Package type of the Lambda function"
  value       = aws_lambda_function.main.package_type
}

output "reserved_concurrent_executions" {
  description = "Reserved concurrent executions of the Lambda function"
  value       = aws_lambda_function.main.reserved_concurrent_executions
}

# VPC Configuration
output "vpc_config" {
  description = "VPC configuration of the Lambda function"
  value = var.vpc_config != null ? {
    vpc_id             = var.vpc_config.vpc_id
    subnet_ids         = aws_lambda_function.main.vpc_config[0].subnet_ids
    security_group_ids = aws_lambda_function.main.vpc_config[0].security_group_ids
    vpc_id             = aws_lambda_function.main.vpc_config[0].vpc_id
  } : null
}

# Environment Variables
output "environment_variables" {
  description = "Environment variables of the Lambda function"
  value       = aws_lambda_function.main.environment
  sensitive   = true
}

# Layers
output "layers" {
  description = "Layers attached to the Lambda function"
  value       = aws_lambda_function.main.layers
}

# Tracing Configuration
output "tracing_config" {
  description = "Tracing configuration of the Lambda function"
  value       = aws_lambda_function.main.tracing_config
}

# Dead Letter Queue
output "dead_letter_config" {
  description = "Dead letter queue configuration"
  value       = aws_lambda_function.main.dead_letter_config
}

# File System Configuration
output "file_system_config" {
  description = "File system configuration"
  value       = aws_lambda_function.main.file_system_config
}

# Resource Tags
output "tags" {
  description = "A map of tags assigned to the resource"
  value       = aws_lambda_function.main.tags_all
}
