# Variables for API Gateway Module

variable "api_name" {
  description = "Name of the API Gateway"
  type        = string
}

variable "api_description" {
  description = "Description of the API Gateway"
  type        = string
  default     = ""
}

variable "api_type" {
  description = "Type of API Gateway"
  type        = string
  default     = "REST"

  validation {
    condition     = contains(["REST", "HTTP"], var.api_type)
    error_message = "API type must be either 'REST' or 'HTTP'."
  }
}

variable "stage_name" {
  description = "Name of the API Gateway stage"
  type        = string
  default     = null
}

variable "environment" {
  description = "Environment name (used as default stage name if stage_name is not provided)"
  type        = string
  
  validation {
    condition     = contains(["dev", "staging", "prod", "dr"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod, dr."
  }
}

# API Configuration
variable "endpoint_type" {
  description = "Type of API Gateway endpoint"
  type        = string
  default     = "REGIONAL"

  validation {
    condition     = contains(["EDGE", "REGIONAL", "PRIVATE"], var.endpoint_type)
    error_message = "Endpoint type must be one of: EDGE, REGIONAL, PRIVATE."
  }
}

variable "vpc_endpoint_ids" {
  description = "List of VPC endpoint IDs (for PRIVATE endpoint type)"
  type        = list(string)
  default     = []
}

variable "api_policy" {
  description = "Policy document for the API Gateway"
  type        = string
  default     = null
}

variable "binary_media_types" {
  description = "List of binary media types supported by the API"
  type        = list(string)
  default     = []
}

# CORS Configuration (HTTP API only)
variable "cors_configuration" {
  description = "CORS configuration for HTTP API"
  type = object({
    allow_credentials = optional(bool)
    allow_headers     = optional(list(string))
    allow_methods     = optional(list(string))
    allow_origins     = optional(list(string))
    expose_headers    = optional(list(string))
    max_age          = optional(number)
  })
  default = null
}

# Deployment Configuration
variable "auto_deploy" {
  description = "Whether to automatically deploy API changes (HTTP API only)"
  type        = bool
  default     = true
}

variable "api_resources" {
  description = "API resources configuration for deployment triggers"
  type        = any
  default     = {}
}

variable "api_methods" {
  description = "API methods configuration for deployment triggers"
  type        = any
  default     = {}
}

# Logging Configuration
variable "log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 14
}

variable "enable_cloudwatch_logging" {
  description = "Enable CloudWatch logging for API Gateway"
  type        = bool
  default     = true
}

variable "xray_tracing_enabled" {
  description = "Enable X-Ray tracing"
  type        = bool
  default     = false
}

# Throttling Configuration
variable "throttle_rate_limit" {
  description = "API Gateway throttle rate limit"
  type        = number
  default     = 10000
}

variable "throttle_burst_limit" {
  description = "API Gateway throttle burst limit"
  type        = number
  default     = 5000
}

# Custom Domain Configuration
variable "domain_name" {
  description = "Custom domain name for the API"
  type        = string
  default     = null
}

variable "certificate_arn" {
  description = "ARN of the certificate for custom domain"
  type        = string
  default     = null
}

variable "domain_endpoint_type" {
  description = "Endpoint type for custom domain"
  type        = string
  default     = "REGIONAL"

  validation {
    condition     = contains(["EDGE", "REGIONAL"], var.domain_endpoint_type)
    error_message = "Domain endpoint type must be either 'EDGE' or 'REGIONAL'."
  }
}

variable "security_policy" {
  description = "Security policy for custom domain"
  type        = string
  default     = "TLS_1_2"

  validation {
    condition     = contains(["TLS_1_0", "TLS_1_2"], var.security_policy)
    error_message = "Security policy must be either 'TLS_1_0' or 'TLS_1_2'."
  }
}

variable "base_path" {
  description = "Base path for API mapping"
  type        = string
  default     = null
}

# Security Configuration
variable "waf_web_acl_arn" {
  description = "ARN of WAF Web ACL to associate with API Gateway"
  type        = string
  default     = null
}

# CloudWatch Alarms
variable "create_cloudwatch_alarms" {
  description = "Whether to create CloudWatch alarms"
  type        = bool
  default     = true
}

variable "alarm_actions" {
  description = "List of ARNs to notify when alarms fire"
  type        = list(string)
  default     = []
}

variable "error_alarm_threshold" {
  description = "Threshold for 4xx error alarm"
  type        = number
  default     = 10
}

variable "latency_alarm_threshold" {
  description = "Threshold for latency alarm (in milliseconds)"
  type        = number
  default     = 1000
}

# Common Tags
variable "tags" {
  description = "A map of tags to assign to resources"
  type        = map(string)
  default     = {}
}

# Integration Configuration
variable "integration_type" {
  description = "Type of integration (for dynamic resource creation)"
  type        = string
  default     = "AWS_PROXY"

  validation {
    condition = contains([
      "AWS", "AWS_PROXY", "HTTP", "HTTP_PROXY", "MOCK"
    ], var.integration_type)
    error_message = "Integration type must be one of: AWS, AWS_PROXY, HTTP, HTTP_PROXY, MOCK."
  }
}

variable "integration_uri" {
  description = "URI for API Gateway integration"
  type        = string
  default     = null
}

# Request/Response Configuration
variable "request_validator_id" {
  description = "ID of the request validator"
  type        = string
  default     = null
}

variable "authorization_type" {
  description = "Type of authorization for API methods"
  type        = string
  default     = "NONE"

  validation {
    condition = contains([
      "NONE", "AWS_IAM", "CUSTOM", "COGNITO_USER_POOLS"
    ], var.authorization_type)
    error_message = "Authorization type must be one of: NONE, AWS_IAM, CUSTOM, COGNITO_USER_POOLS."
  }
}

variable "authorizer_id" {
  description = "ID of the authorizer"
  type        = string
  default     = null
}

# API Key Configuration
variable "api_key_required" {
  description = "Whether API key is required for methods"
  type        = bool
  default     = false
}

# Rate Limiting
variable "usage_plan_name" {
  description = "Name of the usage plan"
  type        = string
  default     = null
}

variable "quota_limit" {
  description = "Maximum number of requests per quota period"
  type        = number
  default     = null
}

variable "quota_period" {
  description = "Time period for quota (DAY, WEEK, MONTH)"
  type        = string
  default     = "MONTH"

  validation {
    condition     = var.quota_period == null || contains(["DAY", "WEEK", "MONTH"], var.quota_period)
    error_message = "Quota period must be one of: DAY, WEEK, MONTH."
  }
}
