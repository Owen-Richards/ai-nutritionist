# Production Environment Variables
# terraform/environments/prod/variables.tf

variable "openai_api_key" {
  description = "OpenAI API key for AI services (production environment)"
  type        = string
  sensitive   = true
}

variable "nutrition_api_key" {
  description = "Nutrition API key for food data (production environment)"
  type        = string
  sensitive   = true
}

variable "owner_email" {
  description = "Email address of the production environment owner for notifications"
  type        = string
  default     = "production@ainutrition.com"
  
  validation {
    condition     = can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.owner_email))
    error_message = "Owner email must be a valid email address."
  }
}

variable "app_version" {
  description = "Application version/tag for container deployment"
  type        = string
  default     = "latest"
}

variable "api_certificate_arn" {
  description = "ACM certificate ARN for custom API domain"
  type        = string
  default     = null
}

variable "management_ip_whitelist" {
  description = "List of IP addresses allowed for management access"
  type        = list(string)
  default     = []
}

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
