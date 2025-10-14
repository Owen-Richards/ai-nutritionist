# Variables for Monitoring Infrastructure

variable "lambda_functions" {
  description = "Map of lambda function names"
  type        = map(string)
  default = {
    message_handler     = "ai-nutritionist-message-handler"
    billing_handler     = "ai-nutritionist-billing-handler"
    scheduler_handler   = "ai-nutritionist-scheduler-handler"
    analytics_handler   = "ai-nutritionist-analytics-handler"
    notification_handler = "ai-nutritionist-notification-handler"
  }
}

variable "dynamodb_tables" {
  description = "Map of DynamoDB table names"
  type        = map(string)
  default = {
    user_data      = "ai-nutritionist-user-data"
    subscriptions  = "ai-nutritionist-subscriptions"
    meal_plans     = "ai-nutritionist-meal-plans"
    analytics      = "ai-nutritionist-analytics"
    notifications  = "ai-nutritionist-notifications"
  }
}

variable "log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 30
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "AI-Nutritionist"
    Environment = "production"
    ManagedBy   = "Terraform"
    Owner       = "DevOps"
  }
}

variable "alert_email" {
  description = "Email address for technical alerts"
  type        = string
  default     = "alerts@ai-nutritionist.com"
}

variable "business_alert_email" {
  description = "Email address for business alerts"
  type        = string
  default     = "business@ai-nutritionist.com"
}

variable "enable_pagerduty" {
  description = "Enable PagerDuty integration"
  type        = bool
  default     = true
}

variable "pagerduty_endpoint" {
  description = "PagerDuty webhook endpoint"
  type        = string
  default     = "https://events.pagerduty.com/integration/YOUR_INTEGRATION_KEY/enqueue"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}
