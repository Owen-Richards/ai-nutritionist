# Conversation State DynamoDB Table
# Purpose: Store conversation state, context, and history for multi-turn interactions
# Architecture: Single-table design with user_id#channel as partition key

resource "aws_dynamodb_table" "conversation_state" {
  name           = "${var.environment}-nutrition-conversations"
  billing_mode   = "PAY_PER_REQUEST"  # On-demand for variable traffic
  hash_key       = "pk"
  range_key      = "sk"

  # Attributes
  attribute {
    name = "pk"
    type = "S"  # Format: "user_id#channel" (e.g., "+15551234567#whatsapp")
  }

  attribute {
    name = "sk"
    type = "S"  # Format: "conversation" (single item per user-channel)
  }

  attribute {
    name = "state"
    type = "S"  # ConversationState enum value
  }

  attribute {
    name = "updated_at"
    type = "N"  # Unix timestamp for ordering
  }

  # TTL for automatic cleanup (GDPR compliance)
  ttl {
    enabled        = true
    attribute_name = "ttl"  # Set to 30 days after last update
  }

  # Global Secondary Index for querying by state
  global_secondary_index {
    name            = "StateIndex"
    hash_key        = "state"
    range_key       = "updated_at"
    projection_type = "ALL"
  }

  # Point-in-time recovery for data protection
  point_in_time_recovery {
    enabled = true
  }

  # Server-side encryption
  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.dynamodb_encryption.arn
  }

  # Tags
  tags = {
    Name        = "Conversation State Table"
    Environment = var.environment
    Service     = "messaging"
    ManagedBy   = "terraform"
    Purpose     = "conversation-state-management"
    Compliance  = "gdpr-compliant"
  }

  # Prevent accidental deletion
  lifecycle {
    prevent_destroy = true
  }
}

# KMS key for DynamoDB encryption
resource "aws_kms_key" "dynamodb_encryption" {
  description             = "KMS key for DynamoDB conversation table encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    Name        = "DynamoDB Conversation Encryption Key"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_kms_alias" "dynamodb_encryption" {
  name          = "alias/${var.environment}-conversation-dynamodb"
  target_key_id = aws_kms_key.dynamodb_encryption.key_id
}

# CloudWatch Alarms for monitoring
resource "aws_cloudwatch_metric_alarm" "conversation_read_throttle" {
  alarm_name          = "${var.environment}-conversation-read-throttle"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "UserErrors"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Alert when conversation table read throttling occurs"
  alarm_actions       = [aws_sns_topic.dynamodb_alarms.arn]

  dimensions = {
    TableName = aws_dynamodb_table.conversation_state.name
  }

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_cloudwatch_metric_alarm" "conversation_write_throttle" {
  alarm_name          = "${var.environment}-conversation-write-throttle"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "UserErrors"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Alert when conversation table write throttling occurs"
  alarm_actions       = [aws_sns_topic.dynamodb_alarms.arn]

  dimensions = {
    TableName = aws_dynamodb_table.conversation_state.name
  }

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# SNS topic for DynamoDB alarms
resource "aws_sns_topic" "dynamodb_alarms" {
  name = "${var.environment}-dynamodb-alarms"

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# IAM policy for Lambda functions to access conversation table
resource "aws_iam_policy" "conversation_table_access" {
  name        = "${var.environment}-conversation-table-access"
  description = "Policy for Lambda functions to access conversation state table"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.conversation_state.arn,
          "${aws_dynamodb_table.conversation_state.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey"
        ]
        Resource = aws_kms_key.dynamodb_encryption.arn
      }
    ]
  })

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# Outputs
output "conversation_table_name" {
  description = "Name of the conversation state DynamoDB table"
  value       = aws_dynamodb_table.conversation_state.name
}

output "conversation_table_arn" {
  description = "ARN of the conversation state DynamoDB table"
  value       = aws_dynamodb_table.conversation_state.arn
}

output "conversation_table_stream_arn" {
  description = "ARN of the DynamoDB stream for conversation table"
  value       = aws_dynamodb_table.conversation_state.stream_arn
}

output "conversation_kms_key_id" {
  description = "ID of the KMS key used for conversation table encryption"
  value       = aws_kms_key.dynamodb_encryption.key_id
}

output "conversation_iam_policy_arn" {
  description = "ARN of the IAM policy for conversation table access"
  value       = aws_iam_policy.conversation_table_access.arn
}

# DynamoDB auto-scaling for provisioned mode (optional, currently using on-demand)
# Uncomment if switching to provisioned capacity

# resource "aws_appautoscaling_target" "conversation_read_target" {
#   max_capacity       = 100
#   min_capacity       = 5
#   resource_id        = "table/${aws_dynamodb_table.conversation_state.name}"
#   scalable_dimension = "dynamodb:table:ReadCapacityUnits"
#   service_namespace  = "dynamodb"
# }

# resource "aws_appautoscaling_policy" "conversation_read_policy" {
#   name               = "${var.environment}-conversation-read-scaling-policy"
#   policy_type        = "TargetTrackingScaling"
#   resource_id        = aws_appautoscaling_target.conversation_read_target.resource_id
#   scalable_dimension = aws_appautoscaling_target.conversation_read_target.scalable_dimension
#   service_namespace  = aws_appautoscaling_target.conversation_read_target.service_namespace

#   target_tracking_scaling_policy_configuration {
#     predefined_metric_specification {
#       predefined_metric_type = "DynamoDBReadCapacityUtilization"
#     }
#     target_value = 70.0
#   }
# }
