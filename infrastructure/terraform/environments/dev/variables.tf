# Development Environment Variables
# terraform/environments/dev/variables.tf

variable "openai_api_key" {
  description = "OpenAI API key for AI services (dev environment)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "nutrition_api_key" {
  description = "Nutrition API key for food data (dev environment)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "owner_email" {
  description = "Email address of the environment owner for notifications"
  type        = string
  default     = "dev-team@ainutrition.com"
  
  validation {
    condition     = can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.owner_email))
    error_message = "Owner email must be a valid email address."
  }
}
