# DynamoDB Tables for AI Nutritionist Assistant

# Main user data table
resource "aws_dynamodb_table" "user_data" {
  name           = "${var.project_name}-users-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "user_id"
  range_key      = "plan_date"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "plan_date"
    type = "S"
  }

  # GDPR compliance - automatic data expiration
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # Backup and recovery
  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  # Encryption at rest
  server_side_encryption {
    enabled = true
  }

  # Deletion protection for production
  deletion_protection_enabled = var.environment == "prod" ? true : false

  tags = merge(
    {
      Name        = "${var.project_name}-users-${var.environment}"
      Purpose     = "User data and meal plans storage"
      DataClass   = "Personal"
      GDPRSubject = "true"
    },
    var.additional_tags
  )
}

# Subscription management table
resource "aws_dynamodb_table" "subscriptions" {
  name           = "${var.project_name}-subscriptions-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "user_phone"

  attribute {
    name = "user_phone"
    type = "S"
  }

  # Stream for real-time subscription changes
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # Backup and recovery
  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  # Encryption at rest
  server_side_encryption {
    enabled     = true
    kms_key_id  = aws_kms_key.dynamodb.arn
  }

  deletion_protection_enabled = var.environment == "prod" ? true : false

  tags = merge(
    {
      Name      = "${var.project_name}-subscriptions-${var.environment}"
      Purpose   = "User subscription management"
      DataClass = "Billing"
    },
    var.additional_tags
  )
}

# Usage tracking table
resource "aws_dynamodb_table" "usage" {
  name           = "${var.project_name}-usage-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "user_phone"
  range_key      = "month"

  attribute {
    name = "user_phone"
    type = "S"
  }

  attribute {
    name = "month"
    type = "S"
  }

  # Auto-expire usage data after retention period
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # Encryption at rest
  server_side_encryption {
    enabled     = true
    kms_key_id  = aws_kms_key.dynamodb.arn
  }

  tags = merge(
    {
      Name      = "${var.project_name}-usage-${var.environment}"
      Purpose   = "API usage tracking and billing"
      DataClass = "Usage"
    },
    var.additional_tags
  )
}

# Prompt cache table for cost optimization
resource "aws_dynamodb_table" "prompt_cache" {
  name           = "${var.project_name}-cache-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "cache_key"

  attribute {
    name = "cache_key"
    type = "S"
  }

  # Cache expiration
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # Encryption at rest
  server_side_encryption {
    enabled     = true
    kms_key_id  = aws_kms_key.dynamodb.arn
  }

  tags = merge(
    {
      Name      = "${var.project_name}-cache-${var.environment}"
      Purpose   = "AI prompt caching for cost optimization"
      DataClass = "Cache"
    },
    var.additional_tags
  )
}

# Multi-user linking table (GDPR compliant)
resource "aws_dynamodb_table" "user_links" {
  count = var.enable_family_sharing ? 1 : 0
  
  name           = "${var.project_name}-user-links-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "primary_user_id"
  range_key      = "linked_user_id"

  attribute {
    name = "primary_user_id"
    type = "S"
  }

  attribute {
    name = "linked_user_id"
    type = "S"
  }

  attribute {
    name = "invite_code"
    type = "S"
  }

  # GSI for invite lookups
  global_secondary_index {
    name     = "InviteCodeIndex"
    hash_key = "invite_code"
    projection_type = "ALL"
  }

  # GDPR compliance - automatic data expiration
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # Backup and recovery
  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  # Encryption at rest
  server_side_encryption {
    enabled     = true
    kms_key_id  = aws_kms_key.dynamodb.arn
  }

  deletion_protection_enabled = var.environment == "prod" ? true : false

  tags = merge(
    {
      Name        = "${var.project_name}-user-links-${var.environment}"
      Purpose     = "GDPR-compliant family nutrition sharing"
      DataClass   = "Personal"
      GDPRSubject = "true"
      Privacy     = "HighSensitivity"
    },
    var.additional_tags
  )
}

# Consent audit table for GDPR compliance
resource "aws_dynamodb_table" "consent_audit" {
  count = var.gdpr_compliance_enabled ? 1 : 0
  
  name           = "${var.project_name}-consent-audit-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "user_identifier_hash"
  range_key      = "timestamp"

  attribute {
    name = "user_identifier_hash"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "action_type"
    type = "S"
  }

  # GSI for action type queries
  global_secondary_index {
    name     = "ActionTypeIndex"
    hash_key = "action_type"
    range_key = "timestamp"
    projection_type = "ALL"
  }

  # Long-term retention for legal compliance
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # Backup and recovery
  point_in_time_recovery {
    enabled = true
  }

  # Encryption at rest with customer-managed key
  server_side_encryption {
    enabled     = true
    kms_key_id  = aws_kms_key.compliance.arn
  }

  deletion_protection_enabled = true # Always protect audit logs

  tags = merge(
    {
      Name        = "${var.project_name}-consent-audit-${var.environment}"
      Purpose     = "GDPR consent audit trail"
      DataClass   = "Audit"
      Compliance  = "GDPR"
      Retention   = "7years"
    },
    var.additional_tags
  )
}
