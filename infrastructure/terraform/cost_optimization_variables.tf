# ===== COST OPTIMIZATION VARIABLES =====

# Budget Configuration
variable "monthly_budget_limit" {
  description = "Monthly budget limit in USD for cost alerts"
  type        = number
  default     = 100
  validation {
    condition     = var.monthly_budget_limit > 0
    error_message = "Monthly budget limit must be greater than 0."
  }
}

variable "lambda_monthly_gb_seconds_limit" {
  description = "Monthly Lambda GB-seconds usage limit"
  type        = number
  default     = 1000
  validation {
    condition     = var.lambda_monthly_gb_seconds_limit > 0
    error_message = "Lambda usage limit must be greater than 0."
  }
}

# Cost Thresholds
variable "lambda_daily_cost_threshold" {
  description = "Daily cost threshold for Lambda functions in USD"
  type        = number
  default     = 10
  validation {
    condition     = var.lambda_daily_cost_threshold > 0
    error_message = "Lambda daily cost threshold must be greater than 0."
  }
}

variable "dynamodb_daily_cost_threshold" {
  description = "Daily cost threshold for DynamoDB in USD"
  type        = number
  default     = 15
  validation {
    condition     = var.dynamodb_daily_cost_threshold > 0
    error_message = "DynamoDB daily cost threshold must be greater than 0."
  }
}

variable "api_gateway_daily_cost_threshold" {
  description = "Daily cost threshold for API Gateway in USD"
  type        = number
  default     = 5
  validation {
    condition     = var.api_gateway_daily_cost_threshold > 0
    error_message = "API Gateway daily cost threshold must be greater than 0."
  }
}

# Cost Allocation Tags
variable "cost_center" {
  description = "Cost center for billing allocation"
  type        = string
  default     = "AI-Nutritionist"
}

variable "billing_group" {
  description = "Billing group for cost allocation"
  type        = string
  default     = "Production"
}

variable "owner_email" {
  description = "Email address for cost alerts and notifications"
  type        = string
  validation {
    condition     = can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.owner_email))
    error_message = "Owner email must be a valid email address."
  }
}

# Automation Settings
variable "enable_auto_scaling" {
  description = "Enable automated scaling optimizations"
  type        = bool
  default     = true
}

variable "enable_automated_cleanup" {
  description = "Enable automated cleanup of unused resources"
  type        = bool
  default     = true
}

variable "enable_cost_anomaly_detection" {
  description = "Enable AWS Cost Anomaly Detection"
  type        = bool
  default     = true
}

# Reserved Capacity Configuration
variable "enable_lambda_provisioned_concurrency" {
  description = "Enable Lambda provisioned concurrency for predictable workloads"
  type        = bool
  default     = false
}

variable "lambda_provisioned_concurrency_limit" {
  description = "Number of Lambda instances to keep warm"
  type        = number
  default     = 5
  validation {
    condition     = var.lambda_provisioned_concurrency_limit >= 1 && var.lambda_provisioned_concurrency_limit <= 1000
    error_message = "Lambda provisioned concurrency limit must be between 1 and 1000."
  }
}

# DynamoDB Cost Optimization
variable "dynamodb_enable_auto_scaling" {
  description = "Enable DynamoDB auto-scaling for cost optimization"
  type        = bool
  default     = true
}

variable "dynamodb_min_read_capacity" {
  description = "Minimum read capacity units for DynamoDB auto-scaling"
  type        = number
  default     = 1
  validation {
    condition     = var.dynamodb_min_read_capacity >= 1
    error_message = "DynamoDB minimum read capacity must be at least 1."
  }
}

variable "dynamodb_max_read_capacity" {
  description = "Maximum read capacity units for DynamoDB auto-scaling"
  type        = number
  default     = 100
  validation {
    condition     = var.dynamodb_max_read_capacity >= var.dynamodb_min_read_capacity
    error_message = "DynamoDB maximum read capacity must be greater than or equal to minimum."
  }
}

variable "dynamodb_min_write_capacity" {
  description = "Minimum write capacity units for DynamoDB auto-scaling"
  type        = number
  default     = 1
  validation {
    condition     = var.dynamodb_min_write_capacity >= 1
    error_message = "DynamoDB minimum write capacity must be at least 1."
  }
}

variable "dynamodb_max_write_capacity" {
  description = "Maximum write capacity units for DynamoDB auto-scaling"
  type        = number
  default     = 100
  validation {
    condition     = var.dynamodb_max_write_capacity >= var.dynamodb_min_write_capacity
    error_message = "DynamoDB maximum write capacity must be greater than or equal to minimum."
  }
}

variable "dynamodb_target_utilization" {
  description = "Target utilization percentage for DynamoDB auto-scaling"
  type        = number
  default     = 70
  validation {
    condition     = var.dynamodb_target_utilization >= 20 && var.dynamodb_target_utilization <= 90
    error_message = "DynamoDB target utilization must be between 20% and 90%."
  }
}

# CloudFront Cost Optimization
variable "cloudfront_price_class" {
  description = "CloudFront price class for cost optimization"
  type        = string
  default     = "PriceClass_100"  # Use only North America and Europe
  validation {
    condition     = contains(["PriceClass_All", "PriceClass_200", "PriceClass_100"], var.cloudfront_price_class)
    error_message = "CloudFront price class must be PriceClass_All, PriceClass_200, or PriceClass_100."
  }
}

variable "cloudfront_cache_ttl_default" {
  description = "Default TTL for CloudFront caching (seconds)"
  type        = number
  default     = 86400  # 24 hours
  validation {
    condition     = var.cloudfront_cache_ttl_default >= 0
    error_message = "CloudFront default TTL must be non-negative."
  }
}

variable "cloudfront_cache_ttl_max" {
  description = "Maximum TTL for CloudFront caching (seconds)"
  type        = number
  default     = 31536000  # 1 year
  validation {
    condition     = var.cloudfront_cache_ttl_max >= var.cloudfront_cache_ttl_default
    error_message = "CloudFront maximum TTL must be greater than or equal to default TTL."
  }
}

# Spot Instance Configuration (for future ECS/Fargate usage)
variable "enable_spot_instances" {
  description = "Enable spot instances for batch processing workloads"
  type        = bool
  default     = false
}

variable "spot_instance_max_price" {
  description = "Maximum price for spot instances (USD per hour)"
  type        = string
  default     = "0.10"
}

# S3 Cost Optimization
variable "s3_storage_class_transition_days" {
  description = "Number of days after which to transition S3 objects to IA storage"
  type        = number
  default     = 30
  validation {
    condition     = var.s3_storage_class_transition_days >= 1
    error_message = "S3 storage class transition days must be at least 1."
  }
}

variable "s3_glacier_transition_days" {
  description = "Number of days after which to transition S3 objects to Glacier"
  type        = number
  default     = 90
  validation {
    condition     = var.s3_glacier_transition_days >= var.s3_storage_class_transition_days
    error_message = "S3 Glacier transition days must be greater than or equal to IA transition days."
  }
}

variable "s3_deep_archive_transition_days" {
  description = "Number of days after which to transition S3 objects to Glacier Deep Archive"
  type        = number
  default     = 365
  validation {
    condition     = var.s3_deep_archive_transition_days >= var.s3_glacier_transition_days
    error_message = "S3 Deep Archive transition days must be greater than or equal to Glacier transition days."
  }
}

# API Gateway Cost Optimization
variable "api_gateway_caching_enabled" {
  description = "Enable API Gateway caching for cost optimization"
  type        = bool
  default     = true
}

variable "api_gateway_cache_cluster_size" {
  description = "API Gateway cache cluster size"
  type        = string
  default     = "0.5"
  validation {
    condition     = contains(["0.5", "1.6", "6.1", "13.5", "28.4", "58.2", "118", "237"], var.api_gateway_cache_cluster_size)
    error_message = "API Gateway cache cluster size must be one of: 0.5, 1.6, 6.1, 13.5, 28.4, 58.2, 118, 237."
  }
}

variable "api_gateway_cache_ttl" {
  description = "API Gateway cache TTL in seconds"
  type        = number
  default     = 300  # 5 minutes
  validation {
    condition     = var.api_gateway_cache_ttl >= 0 && var.api_gateway_cache_ttl <= 3600
    error_message = "API Gateway cache TTL must be between 0 and 3600 seconds."
  }
}

# Monitoring and Alerting Cost Optimization
variable "cloudwatch_log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 30
  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.cloudwatch_log_retention_days)
    error_message = "CloudWatch log retention days must be a valid AWS retention period."
  }
}

variable "enable_detailed_monitoring" {
  description = "Enable detailed CloudWatch monitoring (additional cost)"
  type        = bool
  default     = false
}

variable "cost_optimization_notification_frequency" {
  description = "Frequency for cost optimization notifications (hours)"
  type        = number
  default     = 24
  validation {
    condition     = var.cost_optimization_notification_frequency >= 1 && var.cost_optimization_notification_frequency <= 168
    error_message = "Cost optimization notification frequency must be between 1 and 168 hours."
  }
}

# Resource Cleanup Configuration
variable "lambda_version_retention_count" {
  description = "Number of Lambda versions to retain (older versions are deleted)"
  type        = number
  default     = 3
  validation {
    condition     = var.lambda_version_retention_count >= 1 && var.lambda_version_retention_count <= 10
    error_message = "Lambda version retention count must be between 1 and 10."
  }
}

variable "unused_resource_cleanup_enabled" {
  description = "Enable cleanup of unused resources"
  type        = bool
  default     = true
}

variable "unused_resource_grace_period_days" {
  description = "Grace period (days) before cleaning up unused resources"
  type        = number
  default     = 7
  validation {
    condition     = var.unused_resource_grace_period_days >= 1 && var.unused_resource_grace_period_days <= 30
    error_message = "Unused resource grace period must be between 1 and 30 days."
  }
}

# ElastiCache Cost Optimization (if enabled)
variable "elasticache_node_type" {
  description = "ElastiCache node type for cost optimization"
  type        = string
  default     = "cache.t3.micro"
  validation {
    condition     = can(regex("^cache\\.", var.elasticache_node_type))
    error_message = "ElastiCache node type must start with 'cache.'."
  }
}

variable "elasticache_num_nodes" {
  description = "Number of ElastiCache nodes for cost optimization"
  type        = number
  default     = 1
  validation {
    condition     = var.elasticache_num_nodes >= 1 && var.elasticache_num_nodes <= 20
    error_message = "ElastiCache number of nodes must be between 1 and 20."
  }
}

# Business Hours Optimization
variable "enable_business_hours_scaling" {
  description = "Enable scaling resources based on business hours"
  type        = bool
  default     = false
}

variable "business_hours_start" {
  description = "Business hours start time (UTC, 24-hour format)"
  type        = string
  default     = "08:00"
  validation {
    condition     = can(regex("^([01]?[0-9]|2[0-3]):[0-5][0-9]$", var.business_hours_start))
    error_message = "Business hours start time must be in HH:MM format."
  }
}

variable "business_hours_end" {
  description = "Business hours end time (UTC, 24-hour format)"
  type        = string
  default     = "18:00"
  validation {
    condition     = can(regex("^([01]?[0-9]|2[0-3]):[0-5][0-9]$", var.business_hours_end))
    error_message = "Business hours end time must be in HH:MM format."
  }
}

variable "business_days" {
  description = "Business days for scaling optimization"
  type        = list(string)
  default     = ["MON", "TUE", "WED", "THU", "FRI"]
  validation {
    condition = alltrue([
      for day in var.business_days : contains(["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"], day)
    ])
    error_message = "Business days must be valid day abbreviations (MON, TUE, WED, THU, FRI, SAT, SUN)."
  }
}
