# Outputs for ECS Module

# ECS Cluster
output "cluster_id" {
  description = "ID of the ECS cluster"
  value       = aws_ecs_cluster.main.id
}

output "cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.main.arn
}

output "cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

# ECS Service
output "service_id" {
  description = "ID of the ECS service"
  value       = aws_ecs_service.main.id
}

output "service_arn" {
  description = "ARN of the ECS service"
  value       = aws_ecs_service.main.id
}

output "service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.main.name
}

output "service_cluster" {
  description = "Amazon Resource Name (ARN) of cluster which the service runs on"
  value       = aws_ecs_service.main.cluster
}

output "service_desired_count" {
  description = "Number of instances of the task definition"
  value       = aws_ecs_service.main.desired_count
}

# Task Definition
output "task_definition_arn" {
  description = "Full ARN of the Task Definition"
  value       = aws_ecs_task_definition.main.arn
}

output "task_definition_family" {
  description = "The family of the Task Definition"
  value       = aws_ecs_task_definition.main.family
}

output "task_definition_revision" {
  description = "The revision of the task in a particular family"
  value       = aws_ecs_task_definition.main.revision
}

# IAM Roles
output "task_execution_role_arn" {
  description = "ARN of the task execution role"
  value       = aws_iam_role.ecs_task_execution.arn
}

output "task_role_arn" {
  description = "ARN of the task role"
  value       = aws_iam_role.ecs_task.arn
}

output "task_execution_role_name" {
  description = "Name of the task execution role"
  value       = aws_iam_role.ecs_task_execution.name
}

output "task_role_name" {
  description = "Name of the task role"
  value       = aws_iam_role.ecs_task.name
}

# Security Group
output "security_group_id" {
  description = "ID of the security group"
  value       = aws_security_group.ecs_tasks.id
}

output "security_group_arn" {
  description = "ARN of the security group"
  value       = aws_security_group.ecs_tasks.arn
}

# CloudWatch Log Group
output "log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.ecs.name
}

output "log_group_arn" {
  description = "ARN of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.ecs.arn
}

# Auto Scaling
output "autoscaling_target_resource_id" {
  description = "Resource ID of the autoscaling target"
  value       = var.enable_auto_scaling && var.service_desired_count > 0 ? aws_appautoscaling_target.ecs[0].resource_id : null
}

output "autoscaling_policy_arn" {
  description = "ARN of the autoscaling policy"
  value       = var.enable_auto_scaling && var.service_desired_count > 0 ? aws_appautoscaling_policy.ecs_scale_up[0].arn : null
}

# CloudWatch Alarms
output "cloudwatch_alarm_ids" {
  description = "List of CloudWatch alarm IDs"
  value = var.create_cloudwatch_alarms ? [
    aws_cloudwatch_metric_alarm.ecs_cpu_high[0].id,
    aws_cloudwatch_metric_alarm.ecs_memory_high[0].id
  ] : []
}

# Container Information
output "container_name" {
  description = "Name of the container"
  value       = var.container_name
}

output "container_port" {
  description = "Port exposed by the container"
  value       = var.container_port
}

# Network Configuration
output "subnets" {
  description = "Subnets associated with the service"
  value       = var.subnet_ids
}

output "vpc_id" {
  description = "VPC ID where the service is deployed"
  value       = var.vpc_id
}

# Launch Configuration
output "launch_type" {
  description = "Launch type of the service"
  value       = var.launch_type
}

output "platform_version" {
  description = "Platform version of the service"
  value       = aws_ecs_service.main.platform_version
}

# Capacity Information
output "capacity_providers" {
  description = "Set of capacity providers available for the cluster"
  value       = aws_ecs_cluster_capacity_providers.main.capacity_providers
}

# Service Discovery
output "service_discovery_registry_arn" {
  description = "ARN of the service discovery registry"
  value       = var.service_discovery_registry_arn
}

# Load Balancer
output "target_group_arn" {
  description = "ARN of the target group"
  value       = var.target_group_arn
}

# Resource Tags
output "tags" {
  description = "A map of tags assigned to the resource"
  value       = aws_ecs_service.main.tags_all
}
