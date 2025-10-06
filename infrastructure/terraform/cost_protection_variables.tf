# 💰 COST PROTECTION VARIABLES
# Configuration for budget protection and cost control

variable "monthly_budget_hard_cap" {
  description = "Hard monthly budget cap in USD (emergency shutdown at 95%)"
  type        = number
  default     = 25
  validation {
    condition     = var.monthly_budget_hard_cap >= 5 && var.monthly_budget_hard_cap <= 1000
    error_message = "Monthly budget must be between $5 and $1000."
  }
}

variable "daily_budget_limit" {
  description = "Daily spending limit in USD"
  type        = number
  default     = 3
  validation {
    condition     = var.daily_budget_limit >= 1 && var.daily_budget_limit <= 100
    error_message = "Daily budget must be between $1 and $100."
  }
}

variable "owner_email" {
  description = "Email address for budget alerts and notifications"
  type        = string
  validation {
    condition     = can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.owner_email))
    error_message = "Please provide a valid email address."
  }
}

variable "enable_emergency_shutdown" {
  description = "Enable automatic shutdown at 95% of budget"
  type        = bool
  default     = true
}

variable "enable_billing_alerts" {
  description = "Enable CloudWatch billing alerts"
  type        = bool
  default     = true
}

variable "testing_mode" {
  description = "Enable testing mode with cost optimizations"
  type        = bool
  default     = true
}

# 🛡️ ACCESS CONTROL VARIABLES

variable "max_authorized_users" {
  description = "Maximum number of authorized users"
  type        = number
  default     = 10
  validation {
    condition     = var.max_authorized_users >= 1 && var.max_authorized_users <= 100
    error_message = "Max authorized users must be between 1 and 100."
  }
}

variable "max_daily_requests_per_user" {
  description = "Maximum API requests per user per day"
  type        = number
  default     = 50
  validation {
    condition     = var.max_daily_requests_per_user >= 10 && var.max_daily_requests_per_user <= 1000
    error_message = "Daily requests must be between 10 and 1000."
  }
}

variable "max_monthly_requests_per_user" {
  description = "Maximum API requests per user per month"
  type        = number
  default     = 1000
  validation {
    condition     = var.max_monthly_requests_per_user >= 100 && var.max_monthly_requests_per_user <= 10000
    error_message = "Monthly requests must be between 100 and 10000."
  }
}

variable "authorized_phone_numbers" {
  description = "List of authorized phone numbers (E.164 format)"
  type        = list(string)
  default     = []
  validation {
    condition = alltrue([
      for phone in var.authorized_phone_numbers : can(regex("^\\+[1-9]\\d{1,14}$", phone))
    ])
    error_message = "All phone numbers must be in E.164 format (e.g., +1234567890)."
  }
}

# 🌐 WAF AND SECURITY

variable "enable_waf_protection" {
  description = "Enable WAF protection for API Gateway"
  type        = bool
  default     = true
}

variable "waf_rate_limit" {
  description = "WAF rate limit (requests per 5 minutes)"
  type        = number
  default     = 2000
}

variable "allowed_countries" {
  description = "List of allowed country codes (ISO 3166-1 alpha-2)"
  type        = list(string)
  default     = null
}

# ⚡ PERFORMANCE LIMITS (Testing Mode)

variable "lambda_concurrency_limit" {
  description = "Reserved concurrency for Lambda functions in testing mode"
  type        = number
  default     = 5
  validation {
    condition     = var.lambda_concurrency_limit >= 1 && var.lambda_concurrency_limit <= 100
    error_message = "Lambda concurrency must be between 1 and 100."
  }
}

variable "lambda_memory_size" {
  description = "Lambda memory size in MB"
  type        = number
  default     = 512
  validation {
    condition = contains([
      128, 256, 384, 512, 640, 768, 896, 1024, 1152, 1280, 1408, 1536, 1664, 1792, 1920, 2048,
      2176, 2304, 2432, 2560, 2688, 2816, 2944, 3072, 3200, 3328, 3456, 3584, 3712, 3840, 3968,
      4096, 4224, 4352, 4480, 4608, 4736, 4864, 4992, 5120, 5248, 5376, 5504, 5632, 5760, 5888,
      6016, 6144, 6272, 6400, 6528, 6656, 6784, 6912, 7040, 7168, 7296, 7424, 7552, 7680, 7808,
      7936, 8064, 8192, 8320, 8448, 8576, 8704, 8832, 8960, 9088, 9216, 9344, 9472, 9600, 9728,
      9856, 9984, 10112, 10240
    ], var.lambda_memory_size)
    error_message = "Lambda memory size must be a valid value between 128 MB and 10240 MB."
  }
}

variable "lambda_timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 60
  validation {
    condition     = var.lambda_timeout >= 1 && var.lambda_timeout <= 900
    error_message = "Lambda timeout must be between 1 and 900 seconds."
  }
}

# 📊 MONITORING

variable "enable_detailed_monitoring" {
  description = "Enable detailed CloudWatch monitoring"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 7
  validation {
    condition = contains([
      1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653
    ], var.log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch value."
  }
}

# 🏷️ COMMON TAGS

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "ai-nutritionist"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default = {
    ManagedBy    = "Terraform"
    CostCenter   = "Development"
    Owner        = "Solo Developer"
    Environment  = "Testing"
  }
}
