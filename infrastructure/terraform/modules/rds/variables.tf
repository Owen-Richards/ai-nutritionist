# Variables for RDS Module

variable "identifier" {
  description = "The name of the RDS instance"
  type        = string
}

variable "engine_type" {
  description = "Database engine type"
  type        = string
  default     = "postgres"

  validation {
    condition     = contains(["postgres", "mysql"], var.engine_type)
    error_message = "Engine type must be either 'postgres' or 'mysql'."
  }
}

variable "postgres_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "15.4"
}

variable "mysql_version" {
  description = "MySQL engine version"
  type        = string
  default     = "8.0"
}

variable "instance_class" {
  description = "The RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "allocated_storage" {
  description = "The allocated storage in gigabytes"
  type        = number
  default     = 20
}

variable "max_allocated_storage" {
  description = "The upper limit for storage autoscaling"
  type        = number
  default     = 100
}

variable "storage_type" {
  description = "The storage type for the RDS instance"
  type        = string
  default     = "gp3"

  validation {
    condition     = contains(["gp2", "gp3", "io1", "io2"], var.storage_type)
    error_message = "Storage type must be one of: gp2, gp3, io1, io2."
  }
}

variable "storage_encrypted" {
  description = "Specifies whether the DB instance is encrypted"
  type        = bool
  default     = true
}

variable "kms_key_id" {
  description = "The ARN for the KMS encryption key"
  type        = string
  default     = null
}

variable "kms_deletion_window" {
  description = "The waiting period for KMS key deletion"
  type        = number
  default     = 7
}

# Database Configuration
variable "database_name" {
  description = "The name of the database to create when the DB instance is created"
  type        = string
  default     = null
}

variable "master_username" {
  description = "Username for the master DB user"
  type        = string
  default     = "admin"
}

variable "master_password" {
  description = "Password for the master DB user"
  type        = string
  sensitive   = true
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
  description = "List of CIDR blocks allowed to access the database"
  type        = list(string)
  default     = []
}

variable "allowed_security_groups" {
  description = "List of security group IDs allowed to access the database"
  type        = list(string)
  default     = []
}

variable "additional_security_groups" {
  description = "Additional security group IDs to attach to the RDS instance"
  type        = list(string)
  default     = []
}

variable "publicly_accessible" {
  description = "Bool to control if instance is publicly accessible"
  type        = bool
  default     = false
}

# High Availability
variable "multi_az" {
  description = "Specifies if the RDS instance is multi-AZ"
  type        = bool
  default     = false
}

variable "availability_zone" {
  description = "The Availability Zone of the RDS instance"
  type        = string
  default     = null
}

# Read Replica Configuration
variable "create_read_replica" {
  description = "Whether to create a read replica"
  type        = bool
  default     = false
}

variable "read_replica_instance_class" {
  description = "The instance class for the read replica"
  type        = string
  default     = null
}

variable "read_replica_availability_zone" {
  description = "The AZ for the read replica"
  type        = string
  default     = null
}

# Backup Configuration
variable "backup_retention_period" {
  description = "The days to retain backups for"
  type        = number
  default     = 7
}

variable "backup_window" {
  description = "The daily time range during which automated backups are created"
  type        = string
  default     = "03:00-04:00"
}

variable "delete_automated_backups" {
  description = "Specifies whether to remove automated backups immediately after the DB instance is deleted"
  type        = bool
  default     = true
}

variable "skip_final_snapshot" {
  description = "Determines whether a final snapshot is created before the DB instance is deleted"
  type        = bool
  default     = false
}

# Maintenance Configuration
variable "maintenance_window" {
  description = "The window to perform maintenance in"
  type        = string
  default     = "sun:04:00-sun:05:00"
}

variable "auto_minor_version_upgrade" {
  description = "Indicates that minor engine upgrades will be applied automatically"
  type        = bool
  default     = true
}

variable "allow_major_version_upgrade" {
  description = "Indicates that major version upgrades are allowed"
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
  description = "Name of the DB parameter group to associate"
  type        = string
  default     = null
}

variable "db_parameters" {
  description = "A list of DB parameters to apply"
  type = list(object({
    name  = string
    value = string
  }))
  default = []
}

# Monitoring
variable "monitoring_interval" {
  description = "The interval for collecting enhanced monitoring metrics"
  type        = number
  default     = 0

  validation {
    condition     = contains([0, 1, 5, 10, 15, 30, 60], var.monitoring_interval)
    error_message = "Monitoring interval must be one of: 0, 1, 5, 10, 15, 30, 60."
  }
}

variable "performance_insights_enabled" {
  description = "Specifies whether Performance Insights are enabled"
  type        = bool
  default     = false
}

variable "performance_insights_retention_period" {
  description = "The amount of time in days to retain Performance Insights data"
  type        = number
  default     = 7
}

# Logging
variable "enabled_cloudwatch_logs_exports" {
  description = "List of log types to export to CloudWatch"
  type        = list(string)
  default     = []
}

variable "log_retention_period" {
  description = "The retention period for CloudWatch logs"
  type        = number
  default     = 14
}

# Security
variable "deletion_protection" {
  description = "If the DB instance should have deletion protection enabled"
  type        = bool
  default     = true
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
  default     = 80
}

variable "connection_alarm_threshold" {
  description = "Database connections threshold for alarm"
  type        = number
  default     = 80
}

variable "free_storage_alarm_threshold" {
  description = "Free storage space threshold for alarm (in bytes)"
  type        = number
  default     = 2000000000  # 2GB
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
variable "enable_auto_scaling" {
  description = "Enable storage auto scaling"
  type        = bool
  default     = true
}

variable "iops" {
  description = "The amount of provisioned IOPS (only for io1/io2 storage types)"
  type        = number
  default     = null
}

variable "storage_throughput" {
  description = "Storage throughput value for gp3 storage type"
  type        = number
  default     = null
}
