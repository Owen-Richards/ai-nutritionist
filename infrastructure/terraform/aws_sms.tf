# AWS End User Messaging SMS Service Configuration
# MIGRATION NOTE: Replaces deprecated Amazon Pinpoint for SMS
# Amazon Pinpoint service was deprecated effective October 30, 2026
# The pinpoint-sms-voice-v2 APIs used here will continue to work as AWS End User Messaging

# Phone Pool for SMS messaging with failover support
resource "aws_pinpoint_sms_voice_v2_phone_pool" "ai_nutritionist_pool" {
  count     = var.enable_aws_sms ? 1 : 0
  pool_type = "SHARED"
  
  tags = {
    Name           = "${var.project_name}-${var.environment}-sms-pool"
    Environment    = var.environment
    Project        = var.project_name
    Service        = "aws-end-user-messaging"
    MigrationNote  = "pinpoint-sms-voice-v2-apis-continue-as-aws-end-user-messaging"
  }
}

# Dedicated phone number for the service
resource "aws_pinpoint_sms_voice_v2_phone_number" "ai_nutritionist_number" {
  count              = var.enable_aws_sms ? 1 : 0
  iso_country_code   = var.sms_phone_country
  message_type       = var.sms_message_type
  number_capabilities = ["SMS", "VOICE"]
  number_type        = "LONG_CODE"
  
  pool_id = aws_pinpoint_sms_voice_v2_phone_pool.ai_nutritionist_pool[0].pool_id
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-sms-number"
    Environment = var.environment
    Project     = var.project_name
    Service     = "aws-end-user-messaging"
  }
}

# Configuration Set for message tracking and delivery
resource "aws_pinpoint_sms_voice_v2_configuration_set" "ai_nutritionist_config" {
  count = var.enable_aws_sms ? 1 : 0
  name  = "${var.project_name}-${var.environment}-sms-config"
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-sms-config"
    Environment = var.environment
    Project     = var.project_name
    Service     = "aws-end-user-messaging"
  }
}

# CloudWatch Event Destination for message delivery tracking
resource "aws_pinpoint_sms_voice_v2_event_destination" "message_events" {
  count                  = var.enable_aws_sms ? 1 : 0
  configuration_set_name = aws_pinpoint_sms_voice_v2_configuration_set.ai_nutritionist_config[0].name
  event_destination_name = "message-delivery-events"
  enabled               = true
  
  matching_event_types = [
    "TEXT_DELIVERED",
    "TEXT_DELIVERY_FAILURE",
    "TEXT_SENT",
    "TEXT_BLOCKED"
  ]
  
  cloud_watch_logs_destination {
    log_group_name = "/aws/pinpoint-sms-voice-v2/${var.project_name}"
  }
}

# CloudWatch Log Group for SMS events
resource "aws_cloudwatch_log_group" "sms_events" {
  count             = var.enable_aws_sms ? 1 : 0
  name              = "/aws/pinpoint-sms-voice-v2/${var.project_name}"
  retention_in_days = 30
  
  tags = {
    Name        = "${var.project_name}-sms-events"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Variables for AWS SMS configuration
variable "enable_aws_sms" {
  description = "Enable AWS End User Messaging SMS service (replaced Amazon Pinpoint)"
  type        = bool
  default     = false
}

variable "sms_phone_country" {
  description = "Country code for SMS phone number"
  type        = string
  default     = "US"
}

variable "sms_message_type" {
  description = "SMS message type (TRANSACTIONAL or PROMOTIONAL)"
  type        = string
  default     = "TRANSACTIONAL"
}

# Outputs
output "sms_pool_id" {
  description = "ID of the SMS phone pool"
  value       = var.enable_aws_sms ? aws_pinpoint_sms_voice_v2_phone_pool.ai_nutritionist_pool[0].pool_id : null
}

output "sms_phone_number" {
  description = "Provisioned SMS phone number"
  value       = var.enable_aws_sms ? aws_pinpoint_sms_voice_v2_phone_number.ai_nutritionist_number[0].phone_number : null
}

output "sms_configuration_set" {
  description = "SMS configuration set name"
  value       = var.enable_aws_sms ? aws_pinpoint_sms_voice_v2_configuration_set.ai_nutritionist_config[0].name : null
}
