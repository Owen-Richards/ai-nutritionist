# Variables for Lambda Module

variable "function_name" {
  description = "Name of the Lambda function"
  type        = string
}

variable "function_name_prefix" {
  description = "Prefix for the Lambda function name"
  type        = string
  default     = null
}

# Code Configuration
variable "source_code_path" {
  description = "Path to the source code directory"
  type        = string
  default     = null
}

variable "deployment_package_path" {
  description = "Path to the deployment package (zip file)"
  type        = string
  default     = null
}

variable "source_code_hash" {
  description = "Hash of the source code for deployment package"
  type        = string
  default     = null
}

variable "package_excludes" {
  description = "List of files/directories to exclude from the package"
  type        = list(string)
  default     = [".git", ".terraform", "*.md", "tests"]
}

variable "handler" {
  description = "Lambda function handler"
  type        = string
  default     = "index.handler"
}

variable "runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.11"

  validation {
    condition = contains([
      "python3.8", "python3.9", "python3.10", "python3.11",
      "nodejs16.x", "nodejs18.x", "nodejs20.x",
      "java8", "java11", "java17", "java21",
      "dotnet6", "dotnet8",
      "go1.x", "ruby3.2", "provided.al2", "provided.al2023"
    ], var.runtime)
    error_message = "Runtime must be a valid AWS Lambda runtime."
  }
}

variable "package_type" {
  description = "Package type for Lambda function"
  type        = string
  default     = "Zip"

  validation {
    condition     = contains(["Zip", "Image"], var.package_type)
    error_message = "Package type must be either 'Zip' or 'Image'."
  }
}

variable "image_uri" {
  description = "URI of the container image (for Image package type)"
  type        = string
  default     = null
}

variable "image_config" {
  description = "Configuration for container image"
  type = object({
    command           = optional(list(string))
    entry_point       = optional(list(string))
    working_directory = optional(string)
  })
  default = null
}

# Performance Configuration
variable "memory_size" {
  description = "Memory size for the Lambda function"
  type        = number
  default     = 128

  validation {
    condition     = var.memory_size >= 128 && var.memory_size <= 10240
    error_message = "Memory size must be between 128 and 10240 MB."
  }
}

variable "timeout" {
  description = "Timeout for the Lambda function"
  type        = number
  default     = 3

  validation {
    condition     = var.timeout >= 1 && var.timeout <= 900
    error_message = "Timeout must be between 1 and 900 seconds."
  }
}

variable "reserved_concurrent_executions" {
  description = "Number of reserved concurrent executions"
  type        = number
  default     = null
}

# Environment Configuration
variable "environment_variables" {
  description = "Environment variables for the Lambda function"
  type        = map(string)
  default     = {}
  sensitive   = true
}

variable "kms_key_arn" {
  description = "ARN of the KMS key for environment variable encryption"
  type        = string
  default     = null
}

variable "kms_deletion_window" {
  description = "KMS key deletion window in days"
  type        = number
  default     = 7
}

# VPC Configuration
variable "vpc_config" {
  description = "VPC configuration for the Lambda function"
  type = object({
    vpc_id             = string
    subnet_ids         = list(string)
    security_group_ids = list(string)
  })
  default = null
}

variable "create_security_group" {
  description = "Whether to create a security group for the Lambda function"
  type        = bool
  default     = true
}

variable "allow_http_outbound" {
  description = "Allow HTTP outbound traffic in security group"
  type        = bool
  default     = false
}

variable "security_group_egress_rules" {
  description = "Custom egress rules for the security group"
  type = list(object({
    description     = string
    from_port       = number
    to_port         = number
    protocol        = string
    cidr_blocks     = optional(list(string))
    security_groups = optional(list(string))
  }))
  default = []
}

variable "security_group_ingress_rules" {
  description = "Custom ingress rules for the security group"
  type = list(object({
    description     = string
    from_port       = number
    to_port         = number
    protocol        = string
    cidr_blocks     = optional(list(string))
    security_groups = optional(list(string))
  }))
  default = []
}

# IAM Configuration
variable "policy_statements" {
  description = "Additional IAM policy statements for the Lambda execution role"
  type        = list(any)
  default     = []
}

# Dead Letter Queue
variable "dead_letter_target_arn" {
  description = "ARN of the SQS queue or SNS topic for dead letter queue"
  type        = string
  default     = null
}

# File System Configuration
variable "file_system_config" {
  description = "EFS file system configuration"
  type = object({
    arn              = string
    local_mount_path = string
  })
  default = null
}

# Tracing Configuration
variable "tracing_mode" {
  description = "X-Ray tracing mode"
  type        = string
  default     = "PassThrough"

  validation {
    condition     = contains(["Active", "PassThrough"], var.tracing_mode)
    error_message = "Tracing mode must be either 'Active' or 'PassThrough'."
  }
}

# Layers
variable "layers" {
  description = "List of Lambda layer ARNs"
  type        = list(string)
  default     = []
}

# Function URL Configuration
variable "create_function_url" {
  description = "Whether to create a Lambda function URL"
  type        = bool
  default     = false
}

variable "function_url_auth_type" {
  description = "Authorization type for the function URL"
  type        = string
  default     = "AWS_IAM"

  validation {
    condition     = contains(["AWS_IAM", "NONE"], var.function_url_auth_type)
    error_message = "Function URL auth type must be either 'AWS_IAM' or 'NONE'."
  }
}

variable "function_url_cors" {
  description = "CORS configuration for function URL"
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

# Alias Configuration
variable "create_alias" {
  description = "Whether to create a Lambda alias"
  type        = bool
  default     = false
}

variable "alias_name" {
  description = "Name of the Lambda alias"
  type        = string
  default     = "live"
}

variable "alias_description" {
  description = "Description of the Lambda alias"
  type        = string
  default     = "Live version of the function"
}

variable "alias_function_version" {
  description = "Function version for the alias"
  type        = string
  default     = "$LATEST"
}

variable "alias_routing_config" {
  description = "Routing configuration for the alias"
  type = object({
    additional_version_weights = map(number)
  })
  default = null
}

# API Gateway Integration
variable "api_gateway_execution_arn" {
  description = "Execution ARN of the API Gateway for Lambda permission"
  type        = string
  default     = null
}

# Logging Configuration
variable "log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 14
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
  description = "Threshold for error alarm"
  type        = number
  default     = 1
}

variable "duration_alarm_threshold" {
  description = "Threshold for duration alarm (in milliseconds)"
  type        = number
  default     = 30000
}

variable "throttle_alarm_threshold" {
  description = "Threshold for throttle alarm"
  type        = number
  default     = 1
}

# Common Tags
variable "tags" {
  description = "A map of tags to assign to resources"
  type        = map(string)
  default     = {}
}

# Environment
variable "environment" {
  description = "Environment name"
  type        = string
  
  validation {
    condition     = contains(["dev", "staging", "prod", "dr"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod, dr."
  }
}
