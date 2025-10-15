# AI Nutritionist Infrastructure - Root Module Variables
# Environment-agnostic variable definitions

# General Configuration
variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "ai-nutritionist"
  
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod, dr)"
  type        = string
  
  validation {
    condition     = contains(["dev", "staging", "prod", "dr"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod, dr."
  }
}

variable "owner_email" {
  description = "Email address of the environment owner for notifications"
  type        = string
  
  validation {
    condition     = can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.owner_email))
    error_message = "Owner email must be a valid email address."
  }
}

variable "aws_region" {
  description = "AWS region for primary deployment"
  type        = string
  default     = "us-east-1"
}

variable "dr_region" {
  description = "AWS region for disaster recovery"
  type        = string
  default     = "us-west-2"
}

variable "global_tags" {
  description = "Global tags to apply to all resources"
  type        = map(string)
  default = {
    Project    = "AI-Nutritionist"
    Repository = "ai-nutritionalist"
    Team       = "AI-Development"
  }
}

# Network Configuration
variable "management_cidr" {
  description = "CIDR block for management access"
  type        = string
  default     = "10.0.0.0/8"
}

variable "enable_vpc_flow_logs" {
  description = "Enable VPC flow logs"
  type        = bool
  default     = true
}

variable "enable_vpc_endpoints" {
  description = "Enable VPC endpoints for AWS services"
  type        = bool
  default     = true
}

# Security Configuration
variable "kms_admin_arns" {
  description = "List of ARNs for KMS key administrators"
  type        = list(string)
  default     = []
}

variable "kms_user_arns" {
  description = "List of ARNs for KMS key users"
  type        = list(string)
  default     = []
}

variable "enable_security_logging" {
  description = "Enable comprehensive security logging"
  type        = bool
  default     = true
}

variable "enable_cloudtrail" {
  description = "Enable AWS CloudTrail"
  type        = bool
  default     = true
}

variable "cloudtrail_s3_bucket_name" {
  description = "S3 bucket name for CloudTrail logs"
  type        = string
  default     = null
}

variable "additional_secrets" {
  description = "Additional secrets to create in Secrets Manager"
  type = map(object({
    description       = string
    secret_string     = optional(string)
    generate_password = optional(bool, false)
    username          = optional(string)
  }))
  default = {}
  sensitive = true
}

# Database Configuration
variable "db_name" {
  description = "Database name"
  type        = string
  default     = "ai_nutritionist"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "ainutrition_admin"
}

variable "db_password" {
  description = "Database master password (use Secrets Manager in production)"
  type        = string
  default     = null
  sensitive   = true
}

variable "db_allocated_storage" {
  description = "Database allocated storage in GB"
  type        = number
  default     = 20
}

# Application Configuration
variable "container_image" {
  description = "Container image for the application"
  type        = string
  default     = "nginx:latest" # Replace with actual application image
}

variable "ecs_desired_count" {
  description = "Desired number of ECS service instances"
  type        = number
  default     = 2
}

variable "ecs_min_capacity" {
  description = "Minimum ECS service capacity for auto-scaling"
  type        = number
  default     = 1
}

variable "ecs_max_capacity" {
  description = "Maximum ECS service capacity for auto-scaling"
  type        = number
  default     = 10
}

# API Gateway Configuration
variable "allowed_origins" {
  description = "Allowed origins for CORS"
  type        = list(string)
  default     = ["*"]
}

variable "api_domain_name" {
  description = "Custom domain name for API"
  type        = string
  default     = null
}

variable "api_certificate_arn" {
  description = "ACM certificate ARN for API domain"
  type        = string
  default     = null
}

# External API Keys (sensitive)
variable "openai_api_key" {
  description = "OpenAI API key for AI services"
  type        = string
  default     = ""
  sensitive   = true
}

variable "nutrition_api_key" {
  description = "Nutrition API key for food data"
  type        = string
  default     = ""
  sensitive   = true
}

# Cost Management
variable "enable_cost_monitoring" {
  description = "Enable AWS Budgets for cost monitoring"
  type        = bool
  default     = true
}

variable "monthly_budget_limit" {
  description = "Monthly budget limit in USD"
  type        = string
  default     = "100"
}

variable "budget_notification_emails" {
  description = "Email addresses for budget notifications"
  type        = list(string)
  default     = []
}

# Feature Flags
variable "enable_enhanced_monitoring" {
  description = "Enable enhanced monitoring and logging"
  type        = bool
  default     = true
}

variable "enable_auto_scaling" {
  description = "Enable auto-scaling for ECS services"
  type        = bool
  default     = true
}

variable "enable_backup_automation" {
  description = "Enable automated backup solutions"
  type        = bool
  default     = true
}

# Environment-specific Overrides
variable "custom_vpc_cidr" {
  description = "Custom VPC CIDR block (overrides environment defaults)"
  type        = string
  default     = null
}

variable "custom_availability_zones" {
  description = "Custom availability zones (overrides environment defaults)"
  type        = list(string)
  default     = null
}

variable "force_single_nat_gateway" {
  description = "Force single NAT gateway even in production"
  type        = bool
  default     = false
}

# Advanced Configuration
variable "enable_container_insights" {
  description = "Enable CloudWatch Container Insights for ECS"
  type        = bool
  default     = true
}

variable "enable_xray_tracing" {
  description = "Enable AWS X-Ray tracing"
  type        = bool
  default     = false
}

variable "lambda_reserved_concurrency" {
  description = "Reserved concurrency for Lambda functions"
  type        = number
  default     = null
}

variable "rds_performance_insights_enabled" {
  description = "Enable RDS Performance Insights"
  type        = bool
  default     = true
}

variable "elasticache_snapshot_retention_limit" {
  description = "Number of days to retain ElastiCache snapshots"
  type        = number
  default     = 5
}

# Disaster Recovery
variable "enable_cross_region_backup" {
  description = "Enable cross-region backup for disaster recovery"
  type        = bool
  default     = false
}

variable "cross_region_backup_destination" {
  description = "Destination region for cross-region backups"
  type        = string
  default     = "us-west-2"
}

# Security Hardening
variable "enforce_ssl_only" {
  description = "Enforce SSL/TLS for all connections"
  type        = bool
  default     = true
}

variable "enable_waf" {
  description = "Enable AWS WAF for API Gateway"
  type        = bool
  default     = true
}

variable "ip_whitelist" {
  description = "IP addresses to whitelist for management access"
  type        = list(string)
  default     = []
}

# Compliance and Governance
variable "data_retention_days" {
  description = "Number of days to retain logs and data"
  type        = number
  default     = 90
}

variable "enable_encryption_at_rest" {
  description = "Enable encryption at rest for all supported services"
  type        = bool
  default     = true
}

variable "enable_encryption_in_transit" {
  description = "Enable encryption in transit for all supported services"
  type        = bool
  default     = true
}

variable "compliance_framework" {
  description = "Compliance framework to follow (SOC2, HIPAA, PCI, etc.)"
  type        = string
  default     = "SOC2"
  
  validation {
    condition     = contains(["SOC2", "HIPAA", "PCI", "GDPR", "NONE"], var.compliance_framework)
    error_message = "Compliance framework must be one of: SOC2, HIPAA, PCI, GDPR, NONE."
  }
}
