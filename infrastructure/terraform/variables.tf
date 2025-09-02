# Variables for AI Nutritionist Infrastructure

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "ai-nutritionist"
}

variable "lambda_runtime" {
  description = "Lambda runtime version"
  type        = string
  default     = "python3.11"
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 30
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 256
}

# Privacy and Multi-User Feature Configuration
variable "enable_family_sharing" {
  description = "Enable GDPR-compliant family nutrition sharing"
  type        = bool
  default     = true
}

variable "gdpr_compliance_enabled" {
  description = "Enable GDPR compliance features"
  type        = bool
  default     = true
}

# Monitoring and Alerting
variable "enable_xray_tracing" {
  description = "Enable AWS X-Ray tracing for Lambda functions"
  type        = bool
  default     = true
}

variable "enable_enhanced_monitoring" {
  description = "Enable enhanced CloudWatch monitoring"
  type        = bool
  default     = true
}

variable "cost_alert_threshold" {
  description = "Cost alert threshold in USD"
  type        = number
  default     = 500
}

# Security Configuration
variable "enable_waf" {
  description = "Enable AWS WAF for API Gateway"
  type        = bool
  default     = true
}

# Privacy and Compliance
variable "gdpr_compliance_enabled" {
  description = "Enable GDPR compliance features including consent tracking and audit logs"
  type        = bool
  default     = true
}

variable "enable_family_sharing" {
  description = "Enable family nutrition sharing features with privacy controls"
  type        = bool
  default     = true
}

variable "privacy_mode" {
  description = "Privacy mode setting for data handling"
  type        = string
  default     = "strict"
  validation {
    condition     = contains(["strict", "balanced", "minimal"], var.privacy_mode)
    error_message = "Privacy mode must be one of: strict, balanced, minimal."
  }
}

# Logging and Monitoring
variable "log_level" {
  description = "Application log level"
  type        = string
  default     = "INFO"
  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], var.log_level)
    error_message = "Log level must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL."
  }
}

variable "cloudwatch_log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 30
  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.cloudwatch_log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch retention period."
  }
}

# Cost Optimization
variable "enable_cost_optimization" {
  description = "Enable cost optimization features like prompt caching"
  type        = bool
  default     = true
}

variable "prompt_cache_ttl" {
  description = "Prompt cache TTL in seconds"
  type        = number
  default     = 3600
}

# Security
variable "enable_webhook_validation" {
  description = "Enable webhook signature validation"
  type        = bool
  default     = true
}

# Monitoring and Observability
variable "enable_detailed_monitoring" {
  description = "Enable detailed CloudWatch monitoring"
  type        = bool
  default     = true
}

variable "enable_xray_tracing" {
  description = "Enable X-Ray distributed tracing"
  type        = bool
  default     = true
}

variable "enable_api_gateway_logging" {
  description = "Enable API Gateway access logging"
  type        = bool
  default     = true
}

# Security and WAF
variable "enable_waf" {
  description = "Enable AWS WAF for API Gateway"
  type        = bool
  default     = true
}

variable "waf_rate_limit" {
  description = "WAF rate limit requests per 5-minute period"
  type        = number
  default     = 2000
}

# Custom Domain (optional)
variable "custom_domain_name" {
  description = "Custom domain name for API Gateway"
  type        = string
  default     = ""
}

# CloudFront Configuration
variable "cloudfront_price_class" {
  description = "CloudFront price class"
  type        = string
  default     = "PriceClass_100"
  validation {
    condition     = contains(["PriceClass_100", "PriceClass_200", "PriceClass_All"], var.cloudfront_price_class)
    error_message = "CloudFront price class must be one of: PriceClass_100, PriceClass_200, PriceClass_All."
  }
}

variable "cloudfront_default_ttl" {
  description = "CloudFront default TTL in seconds"
  type        = number
  default     = 86400  # 24 hours
}

variable "cloudfront_max_ttl" {
  description = "CloudFront maximum TTL in seconds"
  type        = number
  default     = 31536000  # 1 year
}

variable "cloudfront_ssl_certificate_arn" {
  description = "SSL certificate ARN for CloudFront (must be in us-east-1)"
  type        = string
  default     = ""
}

variable "enable_cloudfront_waf" {
  description = "Enable WAF for CloudFront"
  type        = bool
  default     = true
}

variable "cloudfront_waf_rate_limit" {
  description = "CloudFront WAF rate limit requests per 5-minute period"
  type        = number
  default     = 10000
}

variable "enable_cloudfront_logging" {
  description = "Enable CloudFront access logging"
  type        = bool
  default     = false  # Disabled by default due to cost
}

variable "cloudfront_logs_retention_days" {
  description = "CloudFront logs retention period in days"
  type        = number
  default     = 30
}

variable "cloudfront_geo_restriction_type" {
  description = "CloudFront geographic restriction type"
  type        = string
  default     = "none"
  validation {
    condition     = contains(["none", "whitelist", "blacklist"], var.cloudfront_geo_restriction_type)
    error_message = "CloudFront geo restriction type must be one of: none, whitelist, blacklist."
  }
}

# Monitoring and Alerting
variable "enable_sns_alerts" {
  description = "Enable SNS alerts for monitoring"
  type        = bool
  default     = true
}

variable "alert_email" {
  description = "Email address for alerts and notifications"
  type        = string
  default     = ""
}

# Cost Management
variable "enable_cost_budgets" {
  description = "Enable AWS Budgets for cost monitoring"
  type        = bool
  default     = true
}

variable "monthly_budget_limit" {
  description = "Monthly budget limit in USD"
  type        = string
  default     = "100"
}

variable "enable_cost_anomaly_detection" {
  description = "Enable AWS Cost Anomaly Detection"
  type        = bool
  default     = true
}

variable "cost_anomaly_threshold" {
  description = "Cost anomaly detection threshold in USD"
  type        = number
  default     = 10
}

variable "cloudfront_geo_restrictions" {
  description = "List of country codes for CloudFront geographic restrictions"
  type        = list(string)
  default     = []
}

variable "ssl_certificate_arn" {
  description = "SSL certificate ARN for custom domain (required if custom_domain_name is set)"
  type        = string
  default     = ""
}

# Lambda Function URLs
variable "enable_lambda_function_urls" {
  description = "Enable Lambda Function URLs for direct webhook access"
  type        = bool
  default     = false
}

# Scheduling
variable "daily_meal_planning_schedule" {
  description = "EventBridge schedule expression for daily meal planning"
  type        = string
  default     = "cron(0 9 * * ? *)"  # 9 AM UTC daily
}

# VPC Configuration
variable "vpc_id" {
  description = "VPC ID for Lambda functions (required if enable_vpc is true)"
  type        = string
  default     = ""
}

variable "vpc_subnet_ids" {
  description = "VPC subnet IDs for Lambda functions (required if enable_vpc is true)"
  type        = list(string)
  default     = []
}

variable "enable_vpc" {
  description = "Deploy Lambda functions in VPC"
  type        = bool
  default     = false # Set to true for production
}

# AI/ML Configuration
variable "bedrock_models" {
  description = "List of Bedrock models to enable"
  type        = list(string)
  default = [
    "amazon.titan-text-express-v1",
    "anthropic.claude-3-haiku-20240307-v1:0"
  ]
}

# Backup and Recovery
variable "enable_point_in_time_recovery" {
  description = "Enable Point-in-Time Recovery for DynamoDB"
  type        = bool
  default     = true
}

variable "backup_retention_days" {
  description = "Backup retention period in days"
  type        = number
  default     = 30
}

# Networking (for VPC deployment)
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24"]
}

# External Service Configuration
variable "twilio_webhook_validation" {
  description = "Enable Twilio webhook signature validation"
  type        = bool
  default     = true
}

variable "stripe_webhook_validation" {
  description = "Enable Stripe webhook signature validation"
  type        = bool
  default     = true
}

# Auto-scaling Configuration
variable "api_gateway_throttling_enabled" {
  description = "Enable API Gateway throttling"
  type        = bool
  default     = true
}

variable "api_gateway_burst_limit" {
  description = "API Gateway burst limit"
  type        = number
  default     = 5000
}

variable "api_gateway_rate_limit" {
  description = "API Gateway rate limit per second"
  type        = number
  default     = 2000
}

# Tags
variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}
