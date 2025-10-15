# Variables for ElastiCache Module

variable "cluster_id" {
  description = "The cluster identifier"
  type        = string
}

variable "engine" {
  description = "Cache engine to use"
  type        = string
  default     = "redis"

  validation {
    condition     = contains(["redis", "memcached"], var.engine)
    error_message = "Engine must be either 'redis' or 'memcached'."
  }
}

variable "redis_version" {
  description = "Redis engine version"
  type        = string
  default     = "7.0"
}

variable "memcached_version" {
  description = "Memcached engine version"
  type        = string
  default     = "1.6.17"
}

variable "node_type" {
  description = "The cache node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "num_cache_clusters" {
  description = "Number of cache clusters (nodes) in the replication group"
  type        = number
  default     = 1
}

variable "num_cache_nodes" {
  description = "Number of cache nodes for Memcached cluster"
  type        = number
  default     = 1
}

# Network Configuration
variable "vpc_id" {
  description = "ID of the VPC where to create security group"
  type        = string
}

variable "subnet_ids" {
  description = "A list of VPC subnet IDs"
  type        = list(string)
}

variable "allowed_cidr_blocks" {
  description = "List of CIDR blocks allowed to access the cache"
  type        = list(string)
  default     = []
}

variable "allowed_security_groups" {
  description = "List of security group IDs allowed to access the cache"
  type        = list(string)
  default     = []
}

variable "additional_security_groups" {
  description = "Additional security group IDs to attach to the cache cluster"
  type        = list(string)
  default     = []
}

variable "availability_zone" {
  description = "The Availability Zone for single-node Redis cluster"
  type        = string
  default     = null
}

# High Availability (Redis only)
variable "automatic_failover_enabled" {
  description = "Specifies whether a read-only replica is automatically promoted to read/write primary if the existing primary fails"
  type        = bool
  default     = false
}

variable "multi_az_enabled" {
  description = "Specifies whether to enable Multi-AZ Support for the replication group"
  type        = bool
  default     = false
}

# Parameter Group
variable "create_parameter_group" {
  description = "Whether to create a custom parameter group"
  type        = bool
  default     = false
}

variable "parameter_group_name" {
  description = "Name of the cache parameter group to associate"
  type        = string
  default     = null
}

variable "cache_parameters" {
  description = "A list of cache parameters to apply"
  type = list(object({
    name  = string
    value = string
  }))
  default = []
}

# Backup Configuration (Redis only)
variable "snapshot_retention_limit" {
  description = "The number of days for which ElastiCache retains automatic cache cluster snapshots"
  type        = number
  default     = 0
}

variable "snapshot_window" {
  description = "The daily time range during which automated backups are created"
  type        = string
  default     = "03:00-05:00"
}

variable "final_snapshot_identifier" {
  description = "The name of your final cache snapshot"
  type        = string
  default     = null
}

# Maintenance Configuration
variable "maintenance_window" {
  description = "The maintenance window"
  type        = string
  default     = "sun:05:00-sun:09:00"
}

variable "auto_minor_version_upgrade" {
  description = "Specifies whether minor version engine upgrades are applied automatically"
  type        = bool
  default     = true
}

# Encryption
variable "at_rest_encryption_enabled" {
  description = "Whether to enable encryption at rest"
  type        = bool
  default     = true
}

variable "transit_encryption_enabled" {
  description = "Whether to enable encryption in transit"
  type        = bool
  default     = true
}

variable "kms_key_id" {
  description = "The ARN of the key that you wish to use if encrypting at rest"
  type        = string
  default     = null
}

variable "kms_deletion_window" {
  description = "The waiting period for KMS key deletion"
  type        = number
  default     = 7
}

variable "auth_token" {
  description = "The password used to access a password protected server"
  type        = string
  default     = null
  sensitive   = true
}

# Logging
variable "enable_logging" {
  description = "Enable CloudWatch logging"
  type        = bool
  default     = true
}

variable "log_retention_period" {
  description = "The retention period for CloudWatch logs"
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
  description = "List of ARNs to notify when the alarm fires"
  type        = list(string)
  default     = []
}

variable "cpu_alarm_threshold" {
  description = "CPU utilization threshold for alarm"
  type        = number
  default     = 75
}

variable "memory_alarm_threshold" {
  description = "Memory utilization threshold for alarm"
  type        = number
  default     = 90
}

variable "evictions_alarm_threshold" {
  description = "Evictions threshold for alarm"
  type        = number
  default     = 10
}

# Common Tags
variable "tags" {
  description = "A map of tags to assign to the resource"
  type        = map(string)
  default     = {}
}

# Environment-specific configurations
variable "environment" {
  description = "Environment name"
  type        = string
  
  validation {
    condition     = contains(["dev", "staging", "prod", "dr"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod, dr."
  }
}

# Cost optimization
variable "enable_auto_failover" {
  description = "Enable auto failover for Redis clusters"
  type        = bool
  default     = false
}

variable "preferred_cache_cluster_azs" {
  description = "A list of EC2 availability zones in which the replication group's cache clusters will be created"
  type        = list(string)
  default     = null
}

# Notification Configuration
variable "notification_topic_arn" {
  description = "An ARN of an SNS topic to send ElastiCache notifications to"
  type        = string
  default     = null
}
