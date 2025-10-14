# Variables for Security Module

variable "name_prefix" {
  description = "Prefix for naming resources"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
  
  validation {
    condition     = contains(["dev", "staging", "prod", "dr"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod, dr."
  }
}

# KMS Configuration
variable "kms_keys" {
  description = "Map of KMS keys to create"
  type = map(object({
    description             = string
    deletion_window_in_days = optional(number)
    enable_key_rotation     = optional(bool)
    multi_region           = optional(bool)
    policy                 = optional(string)
    admin_arns             = optional(list(string))
    user_arns              = optional(list(string))
  }))
  default = {}
}

# Secrets Manager Configuration
variable "secrets" {
  description = "Map of secrets to create in Secrets Manager"
  type = map(object({
    description            = string
    secret_string          = optional(string)
    generate_password      = optional(bool)
    password_length        = optional(number)
    include_special        = optional(bool)
    include_upper          = optional(bool)
    include_lower          = optional(bool)
    include_numeric        = optional(bool)
    username              = optional(string)
    recovery_window_in_days = optional(number)
  }))
  default = {}
  sensitive = true
}

# IAM Configuration
variable "iam_roles" {
  description = "Map of IAM roles to create"
  type = map(object({
    assume_role_policy   = string
    path                = optional(string)
    max_session_duration = optional(number)
    policy_arns         = optional(list(string))
    inline_policies     = optional(map(string))
  }))
  default = {}
}

variable "iam_policies" {
  description = "Map of IAM policies to create"
  type = map(object({
    description = string
    policy      = string
    path        = optional(string)
  }))
  default = {}
}

variable "iam_groups" {
  description = "Map of IAM groups to create"
  type = map(object({
    path        = optional(string)
    policy_arns = optional(list(string))
  }))
  default = {}
}

variable "iam_users" {
  description = "Map of IAM users to create"
  type = map(object({
    path   = optional(string)
    groups = optional(list(string))
  }))
  default = {}
}

# Security Groups Configuration
variable "security_groups" {
  description = "Map of security groups to create"
  type = map(object({
    description = string
    vpc_id      = string
    ingress_rules = optional(list(object({
      description      = string
      from_port        = number
      to_port          = number
      protocol         = string
      cidr_blocks      = optional(list(string))
      ipv6_cidr_blocks = optional(list(string))
      security_groups  = optional(list(string))
      self             = optional(bool)
    })))
    egress_rules = optional(list(object({
      description      = string
      from_port        = number
      to_port          = number
      protocol         = string
      cidr_blocks      = optional(list(string))
      ipv6_cidr_blocks = optional(list(string))
      security_groups  = optional(list(string))
      self             = optional(bool)
    })))
    complex_ingress_rules = optional(list(object({
      description              = string
      from_port                = number
      to_port                  = number
      protocol                 = string
      cidr_blocks              = optional(list(string))
      ipv6_cidr_blocks         = optional(list(string))
      source_security_group_id = optional(string)
      self                     = optional(bool)
    })))
    complex_egress_rules = optional(list(object({
      description              = string
      from_port                = number
      to_port                  = number
      protocol                 = string
      cidr_blocks              = optional(list(string))
      ipv6_cidr_blocks         = optional(list(string))
      source_security_group_id = optional(string)
      self                     = optional(bool)
    })))
  }))
  default = {}
}

# Logging Configuration
variable "enable_security_logging" {
  description = "Enable security logging to CloudWatch"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "Log retention period in days"
  type        = number
  default     = 90
}

# CloudTrail Configuration
variable "enable_cloudtrail" {
  description = "Enable CloudTrail for API logging"
  type        = bool
  default     = false
}

variable "cloudtrail_s3_bucket_name" {
  description = "S3 bucket name for CloudTrail logs"
  type        = string
  default     = null
}

# Common Tags
variable "tags" {
  description = "A map of tags to assign to resources"
  type        = map(string)
  default     = {}
}

# Default Security Groups
variable "create_default_security_groups" {
  description = "Create default security groups for common services"
  type        = bool
  default     = true
}

variable "vpc_id" {
  description = "VPC ID for default security groups"
  type        = string
  default     = null
}

variable "vpc_cidr" {
  description = "VPC CIDR block for default security group rules"
  type        = string
  default     = null
}

# Password Policy
variable "password_policy" {
  description = "Account password policy configuration"
  type = object({
    minimum_password_length        = optional(number)
    require_lowercase_characters   = optional(bool)
    require_uppercase_characters   = optional(bool)
    require_numbers               = optional(bool)
    require_symbols               = optional(bool)
    allow_users_to_change_password = optional(bool)
    max_password_age              = optional(number)
    password_reuse_prevention     = optional(number)
  })
  default = null
}

# Access Analyzer
variable "enable_access_analyzer" {
  description = "Enable IAM Access Analyzer"
  type        = bool
  default     = true
}

variable "access_analyzer_name" {
  description = "Name for the IAM Access Analyzer"
  type        = string
  default     = null
}

# GuardDuty
variable "enable_guardduty" {
  description = "Enable Amazon GuardDuty"
  type        = bool
  default     = false
}

variable "guardduty_finding_publishing_frequency" {
  description = "GuardDuty finding publishing frequency"
  type        = string
  default     = "SIX_HOURS"

  validation {
    condition = contains([
      "FIFTEEN_MINUTES", "ONE_HOUR", "SIX_HOURS"
    ], var.guardduty_finding_publishing_frequency)
    error_message = "GuardDuty finding publishing frequency must be one of: FIFTEEN_MINUTES, ONE_HOUR, SIX_HOURS."
  }
}

# Security Hub
variable "enable_security_hub" {
  description = "Enable AWS Security Hub"
  type        = bool
  default     = false
}

variable "security_hub_standards" {
  description = "List of Security Hub standards to enable"
  type        = list(string)
  default     = ["aws-foundational-security-standard"]
}

# WAF Configuration
variable "enable_waf" {
  description = "Enable AWS WAF"
  type        = bool
  default     = false
}

variable "waf_scope" {
  description = "WAF scope (REGIONAL or CLOUDFRONT)"
  type        = string
  default     = "REGIONAL"

  validation {
    condition     = contains(["REGIONAL", "CLOUDFRONT"], var.waf_scope)
    error_message = "WAF scope must be either 'REGIONAL' or 'CLOUDFRONT'."
  }
}

# Config
variable "enable_config" {
  description = "Enable AWS Config"
  type        = bool
  default     = false
}

variable "config_s3_bucket_name" {
  description = "S3 bucket name for Config"
  type        = string
  default     = null
}
