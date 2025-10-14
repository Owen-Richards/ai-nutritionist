# AI Nutritionist Infrastructure - Root Module Outputs
# Comprehensive outputs for integration with other systems

# Network Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = module.vpc.vpc_cidr_block
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = module.vpc.public_subnet_ids
}

output "private_app_subnet_ids" {
  description = "IDs of the private application subnets"
  value       = module.vpc.private_app_subnet_ids
}

output "private_db_subnet_ids" {
  description = "IDs of the private database subnets"
  value       = module.vpc.private_db_subnet_ids
}

output "nat_gateway_ids" {
  description = "IDs of the NAT gateways"
  value       = module.vpc.nat_gateway_ids
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = module.vpc.internet_gateway_id
}

# Security Outputs
output "kms_key_ids" {
  description = "IDs of KMS keys"
  value       = module.security.kms_key_ids
  sensitive   = true
}

output "kms_key_arns" {
  description = "ARNs of KMS keys"
  value       = module.security.kms_key_arns
  sensitive   = true
}

output "secret_arns" {
  description = "ARNs of Secrets Manager secrets"
  value       = module.security.secret_arns
  sensitive   = true
}

output "security_group_ids" {
  description = "IDs of security groups"
  value       = module.security.security_group_ids
}

output "iam_role_arns" {
  description = "ARNs of IAM roles"
  value       = module.security.iam_role_arns
}

# Database Outputs
output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = module.rds.db_instance_endpoint
  sensitive   = true
}

output "rds_port" {
  description = "RDS instance port"
  value       = module.rds.db_instance_port
}

output "rds_database_name" {
  description = "RDS database name"
  value       = module.rds.db_instance_database_name
}

output "rds_username" {
  description = "RDS master username"
  value       = module.rds.db_instance_username
  sensitive   = true
}

output "rds_parameter_group_name" {
  description = "RDS parameter group name"
  value       = module.rds.db_parameter_group_name
}

output "rds_subnet_group_name" {
  description = "RDS subnet group name"
  value       = module.rds.db_subnet_group_name
}

# Cache Outputs
output "elasticache_cluster_id" {
  description = "ElastiCache cluster ID"
  value       = module.elasticache.cluster_id
}

output "elasticache_primary_endpoint" {
  description = "ElastiCache primary endpoint"
  value       = module.elasticache.primary_endpoint_address
  sensitive   = true
}

output "elasticache_port" {
  description = "ElastiCache port"
  value       = module.elasticache.port
}

output "elasticache_auth_token" {
  description = "ElastiCache auth token"
  value       = module.elasticache.auth_token
  sensitive   = true
}

# Container Orchestration Outputs
output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}

output "ecs_cluster_arn" {
  description = "ECS cluster ARN"
  value       = module.ecs.cluster_arn
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = module.ecs.service_name
}

output "ecs_task_definition_arn" {
  description = "ECS task definition ARN"
  value       = module.ecs.task_definition_arn
}

output "ecs_service_discovery_namespace" {
  description = "ECS service discovery namespace"
  value       = module.ecs.service_discovery_namespace_name
}

# API Gateway Outputs
output "api_gateway_id" {
  description = "API Gateway ID"
  value       = module.api_gateway.http_api_id
}

output "api_gateway_endpoint" {
  description = "API Gateway endpoint URL"
  value       = module.api_gateway.http_api_endpoint
}

output "api_gateway_stage_name" {
  description = "API Gateway stage name"
  value       = module.api_gateway.stage_name
}

output "api_gateway_custom_domain" {
  description = "API Gateway custom domain name"
  value       = module.api_gateway.custom_domain_name
}

# Lambda Function Outputs
output "lambda_function_names" {
  description = "Names of Lambda functions"
  value = {
    nutrition_processor = module.lambda_nutrition_processor.function_name
  }
}

output "lambda_function_arns" {
  description = "ARNs of Lambda functions"
  value = {
    nutrition_processor = module.lambda_nutrition_processor.function_arn
  }
}

output "lambda_function_invoke_arns" {
  description = "Invoke ARNs of Lambda functions"
  value = {
    nutrition_processor = module.lambda_nutrition_processor.invoke_arn
  }
}

# Load Balancer Outputs (if ALB is created)
output "load_balancer_dns_name" {
  description = "DNS name of the load balancer"
  value       = try(module.ecs.load_balancer_dns_name, null)
}

output "load_balancer_zone_id" {
  description = "Zone ID of the load balancer"
  value       = try(module.ecs.load_balancer_zone_id, null)
}

# Monitoring and Logging Outputs
output "cloudwatch_log_groups" {
  description = "CloudWatch log group names"
  value = {
    ecs_tasks    = try(module.ecs.cloudwatch_log_group_name, null)
    lambda_functions = {
      nutrition_processor = module.lambda_nutrition_processor.cloudwatch_log_group_name
    }
    vpc_flow_logs = try(module.vpc.flow_log_group_name, null)
  }
}

# Cost Monitoring Outputs
output "budget_name" {
  description = "AWS Budget name"
  value       = var.enable_cost_monitoring ? aws_budgets_budget.main[0].name : null
}

# Environment Information
output "environment_config" {
  description = "Environment configuration summary"
  value = {
    environment    = var.environment
    aws_region     = var.aws_region
    project_name   = var.project_name
    vpc_cidr       = local.env_config.vpc_cidr
    multi_az       = local.env_config.multi_az
    auto_scaling   = local.env_config.auto_scaling
    instance_types = local.env_config.instance_types
  }
}

# Connection Strings (for application configuration)
output "database_connection_string" {
  description = "Database connection string template"
  value       = "postgresql://${module.rds.db_instance_username}:PASSWORD@${module.rds.db_instance_endpoint}:${module.rds.db_instance_port}/${module.rds.db_instance_database_name}"
  sensitive   = true
}

output "redis_connection_string" {
  description = "Redis connection string"
  value       = "redis://${module.elasticache.primary_endpoint_address}:${module.elasticache.port}"
  sensitive   = true
}

# Resource Summary
output "resource_summary" {
  description = "Summary of created resources"
  value = {
    vpc = {
      id               = module.vpc.vpc_id
      cidr             = module.vpc.vpc_cidr_block
      availability_zones = local.env_config.availability_zones
    }
    database = {
      endpoint      = module.rds.db_instance_endpoint
      engine        = "postgres"
      instance_class = local.env_config.instance_types.rds
      multi_az      = local.env_config.multi_az
    }
    cache = {
      endpoint      = module.elasticache.primary_endpoint_address
      engine        = "redis"
      node_type     = local.env_config.instance_types.cache
      num_nodes     = local.env_config.multi_az ? 2 : 1
    }
    compute = {
      cluster_name     = module.ecs.cluster_name
      desired_capacity = var.ecs_desired_count
      auto_scaling     = local.env_config.auto_scaling
    }
    api = {
      endpoint     = module.api_gateway.http_api_endpoint
      custom_domain = module.api_gateway.custom_domain_name
    }
    lambda_functions = length([
      module.lambda_nutrition_processor.function_name
    ])
    security_groups = length(keys(module.security.security_group_ids))
    kms_keys       = length(keys(module.security.kms_key_ids))
    secrets        = length(keys(module.security.secret_arns))
  }
}

# Deployment Information
output "deployment_info" {
  description = "Information about this deployment"
  value = {
    terraform_version = ">=1.5"
    aws_provider_version = "~>5.0"
    deployment_time = timestamp()
    environment = var.environment
    region = data.aws_region.current.name
    account_id = data.aws_caller_identity.current.account_id
    tags = local.common_tags
  }
}
