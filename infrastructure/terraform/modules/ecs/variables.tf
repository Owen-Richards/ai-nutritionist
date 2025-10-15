# Variables for ECS Module

variable "cluster_name" {
  description = "Name of the ECS cluster"
  type        = string
}

variable "launch_type" {
  description = "Launch type for ECS service"
  type        = string
  default     = "FARGATE"

  validation {
    condition     = contains(["EC2", "FARGATE"], var.launch_type)
    error_message = "Launch type must be either 'EC2' or 'FARGATE'."
  }
}

# Task Definition Configuration
variable "task_definition_family" {
  description = "Family name for the task definition"
  type        = string
}

variable "container_name" {
  description = "Name of the container"
  type        = string
}

variable "container_image" {
  description = "Docker image for the container"
  type        = string
}

variable "container_port" {
  description = "Port exposed by the container"
  type        = number
  default     = 80
}

variable "container_cpu" {
  description = "CPU units for the container (EC2 launch type)"
  type        = number
  default     = 256
}

variable "container_memory" {
  description = "Memory for the container (EC2 launch type)"
  type        = number
  default     = 512
}

variable "container_memory_reservation" {
  description = "Soft memory limit for the container (EC2 launch type)"
  type        = number
  default     = 256
}

# Fargate Configuration
variable "fargate_cpu" {
  description = "CPU units for Fargate task"
  type        = number
  default     = 256

  validation {
    condition = contains([
      256, 512, 1024, 2048, 4096, 8192, 16384
    ], var.fargate_cpu)
    error_message = "Fargate CPU must be one of: 256, 512, 1024, 2048, 4096, 8192, 16384."
  }
}

variable "fargate_memory" {
  description = "Memory for Fargate task"
  type        = number
  default     = 512
}

variable "network_mode" {
  description = "Network mode for task definition"
  type        = string
  default     = "awsvpc"

  validation {
    condition     = contains(["none", "bridge", "awsvpc", "host"], var.network_mode)
    error_message = "Network mode must be one of: none, bridge, awsvpc, host."
  }
}

variable "platform_version" {
  description = "Platform version for Fargate"
  type        = string
  default     = "LATEST"
}

# Service Configuration
variable "service_name" {
  description = "Name of the ECS service"
  type        = string
}

variable "service_desired_count" {
  description = "Desired number of running tasks"
  type        = number
  default     = 1
}

# Network Configuration
variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for ECS service"
  type        = list(string)
}

variable "allowed_security_groups" {
  description = "List of security group IDs allowed to access the service"
  type        = list(string)
  default     = []
}

variable "allowed_cidr_blocks" {
  description = "List of CIDR blocks allowed to access the service"
  type        = list(string)
  default     = []
}

variable "additional_security_groups" {
  description = "Additional security group IDs to attach to the service"
  type        = list(string)
  default     = []
}

variable "assign_public_ip" {
  description = "Whether to assign a public IP to tasks"
  type        = bool
  default     = false
}

# Load Balancer Configuration
variable "target_group_arn" {
  description = "ARN of the target group for load balancer"
  type        = string
  default     = null
}

# Service Discovery
variable "service_discovery_registry_arn" {
  description = "ARN of the service discovery registry"
  type        = string
  default     = null
}

# Environment Variables and Secrets
variable "environment_variables" {
  description = "Environment variables for the container"
  type        = map(string)
  default     = {}
}

variable "secrets" {
  description = "Secrets for the container (from SSM or Secrets Manager)"
  type        = map(string)
  default     = {}
}

# Health Check Configuration
variable "health_check" {
  description = "Health check configuration for the container"
  type = object({
    command      = list(string)
    interval     = number
    timeout      = number
    retries      = number
    start_period = number
  })
  default = null
}

# Deployment Configuration
variable "deployment_maximum_percent" {
  description = "Maximum percentage of tasks that can be running during deployment"
  type        = number
  default     = 200
}

variable "deployment_minimum_healthy_percent" {
  description = "Minimum percentage of tasks that must remain healthy during deployment"
  type        = number
  default     = 100
}

variable "enable_circuit_breaker" {
  description = "Enable deployment circuit breaker"
  type        = bool
  default     = true
}

variable "enable_circuit_breaker_rollback" {
  description = "Enable automatic rollback on circuit breaker"
  type        = bool
  default     = true
}

# Auto Scaling Configuration
variable "enable_auto_scaling" {
  description = "Enable auto scaling for the ECS service"
  type        = bool
  default     = false
}

variable "auto_scaling_min_capacity" {
  description = "Minimum number of tasks for auto scaling"
  type        = number
  default     = 1
}

variable "auto_scaling_max_capacity" {
  description = "Maximum number of tasks for auto scaling"
  type        = number
  default     = 10
}

variable "auto_scaling_metric_type" {
  description = "Metric type for auto scaling"
  type        = string
  default     = "ECSServiceAverageCPUUtilization"

  validation {
    condition = contains([
      "ECSServiceAverageCPUUtilization",
      "ECSServiceAverageMemoryUtilization"
    ], var.auto_scaling_metric_type)
    error_message = "Auto scaling metric type must be ECSServiceAverageCPUUtilization or ECSServiceAverageMemoryUtilization."
  }
}

variable "auto_scaling_target_value" {
  description = "Target value for auto scaling metric"
  type        = number
  default     = 70
}

variable "auto_scaling_scale_in_cooldown" {
  description = "Scale in cooldown period in seconds"
  type        = number
  default     = 300
}

variable "auto_scaling_scale_out_cooldown" {
  description = "Scale out cooldown period in seconds"
  type        = number
  default     = 300
}

# Capacity Providers
variable "capacity_providers" {
  description = "List of capacity providers"
  type        = list(string)
  default     = []
}

variable "capacity_provider_strategy" {
  description = "Capacity provider strategy"
  type = list(object({
    capacity_provider = string
    weight           = number
    base             = optional(number)
  }))
  default = []
}

variable "enable_spot_instances" {
  description = "Enable Spot instances for cost optimization"
  type        = bool
  default     = false
}

# Monitoring and Logging
variable "container_insights_enabled" {
  description = "Enable CloudWatch Container Insights"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "Log retention period in days"
  type        = number
  default     = 14
}

# IAM Configuration
variable "secrets_manager_arns" {
  description = "List of Secrets Manager ARNs the task can access"
  type        = list(string)
  default     = []
}

variable "ssm_parameter_arns" {
  description = "List of SSM Parameter Store ARNs the task can access"
  type        = list(string)
  default     = []
}

variable "additional_task_policy_statements" {
  description = "Additional IAM policy statements for the task role"
  type        = list(any)
  default     = []
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

variable "cpu_alarm_threshold" {
  description = "CPU utilization threshold for alarm"
  type        = number
  default     = 80
}

variable "memory_alarm_threshold" {
  description = "Memory utilization threshold for alarm"
  type        = number
  default     = 80
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
