# AWS End User Messaging SMS Service Configuration
# This replaces Twilio for 2-way SMS communication

# Phone Pool for SMS messaging with failover support
resource "aws_pinpoint_sms_voice_v2_phone_pool" "ai_nutritionist_pool" {
  count     = var.enable_aws_sms ? 1 : 0
  pool_type = "SHARED"
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-sms-pool"
    Environment = var.environment
    Project     = var.project_name
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
    "TEXT_BLOCKED",
    "TEXT_CARRIER_BLOCKED",
    "TEXT_INVALID",
    "TEXT_SPAM",
    "TEXT_TTL_EXPIRED",
    "TEXT_UNKNOWN_ERROR"
  ]
  
  cloud_watch_logs_destination {
    log_group_name = aws_cloudwatch_log_group.sms_events[0].name
  }
}

# CloudWatch Log Group for SMS events
resource "aws_cloudwatch_log_group" "sms_events" {
  count             = var.enable_aws_sms ? 1 : 0
  name              = "/aws/sms/${var.project_name}-${var.environment}"
  retention_in_days = var.sms_retention_days
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-sms-logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

# SQS Queue for inbound SMS messages
resource "aws_sqs_queue" "inbound_sms" {
  count                     = var.enable_aws_sms ? 1 : 0
  name                      = "${var.project_name}-${var.environment}-inbound-sms"
  delay_seconds             = 0
  max_message_size          = 262144
  message_retention_seconds = 1209600
  receive_wait_time_seconds = 10
  
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.inbound_sms_dlq[0].arn
    maxReceiveCount     = 3
  })
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-inbound-sms"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Dead Letter Queue for failed inbound messages
resource "aws_sqs_queue" "inbound_sms_dlq" {
  count = var.enable_aws_sms ? 1 : 0
  name  = "${var.project_name}-${var.environment}-inbound-sms-dlq"
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-inbound-sms-dlq"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Lambda function for processing inbound SMS messages
resource "aws_lambda_function" "inbound_sms_processor" {
  count           = var.enable_aws_sms ? 1 : 0
  filename        = "lambda_functions.zip"
  function_name   = "${var.project_name}-${var.environment}-inbound-sms-processor"
  role           = aws_iam_role.inbound_sms_lambda_role[0].arn
  handler        = "handlers.aws_sms_handler.lambda_handler"
  runtime        = var.lambda_runtime
  timeout        = var.lambda_timeout
  memory_size    = var.lambda_memory_size
  
  environment {
    variables = {
      DYNAMODB_TABLE    = aws_dynamodb_table.users.name
      SQS_QUEUE_URL     = aws_sqs_queue.inbound_sms[0].url
      SMS_CONFIG_SET    = aws_pinpoint_sms_voice_v2_configuration_set.ai_nutritionist_config[0].name
      PHONE_POOL_ID     = aws_pinpoint_sms_voice_v2_phone_pool.ai_nutritionist_pool[0].pool_id
      ENVIRONMENT       = var.environment
    }
  }
  
  depends_on = [
    aws_iam_role_policy_attachment.inbound_sms_lambda_policy,
    aws_cloudwatch_log_group.inbound_sms_lambda_logs,
  ]
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-inbound-sms-processor"
    Environment = var.environment
    Project     = var.project_name
  }
}

# CloudWatch Log Group for inbound SMS Lambda
resource "aws_cloudwatch_log_group" "inbound_sms_lambda_logs" {
  count             = var.enable_aws_sms ? 1 : 0
  name              = "/aws/lambda/${var.project_name}-${var.environment}-inbound-sms-processor"
  retention_in_days = 14
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-inbound-sms-logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Event Source Mapping for SQS to Lambda
resource "aws_lambda_event_source_mapping" "inbound_sms_trigger" {
  count            = var.enable_aws_sms ? 1 : 0
  event_source_arn = aws_sqs_queue.inbound_sms[0].arn
  function_name    = aws_lambda_function.inbound_sms_processor[0].arn
  batch_size       = 10
  
  depends_on = [aws_iam_role_policy_attachment.inbound_sms_lambda_policy]
}

# IAM Role for inbound SMS Lambda function
resource "aws_iam_role" "inbound_sms_lambda_role" {
  count = var.enable_aws_sms ? 1 : 0
  name  = "${var.project_name}-${var.environment}-inbound-sms-lambda-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-inbound-sms-lambda-role"
    Environment = var.environment
    Project     = var.project_name
  }
}

# IAM Policy for inbound SMS Lambda
resource "aws_iam_role_policy" "inbound_sms_lambda_policy" {
  count = var.enable_aws_sms ? 1 : 0
  name  = "${var.project_name}-${var.environment}-inbound-sms-lambda-policy"
  role  = aws_iam_role.inbound_sms_lambda_role[0].id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = [
          aws_sqs_queue.inbound_sms[0].arn,
          aws_sqs_queue.inbound_sms_dlq[0].arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.users.arn,
          "${aws_dynamodb_table.users.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sms-voice:SendTextMessage",
          "sms-voice:SendVoiceMessage",
          "sms-voice:DescribePhoneNumbers",
          "sms-voice:DescribeConfiguration*"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = "arn:aws:ssm:${var.aws_region}:*:parameter/${var.project_name}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = "arn:aws:bedrock:${var.aws_region}::foundation-model/*"
      }
    ]
  })
}

# Attach basic execution policy
resource "aws_iam_role_policy_attachment" "inbound_sms_lambda_policy" {
  count      = var.enable_aws_sms ? 1 : 0
  role       = aws_iam_role.inbound_sms_lambda_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Opt-out list for managing unsubscribe requests
resource "aws_pinpoint_sms_voice_v2_opt_out_list" "ai_nutritionist_optout" {
  count = var.enable_aws_sms ? 1 : 0
  name  = "${var.project_name}-${var.environment}-optout-list"
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-optout"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Associate phone pool with opt-out list
resource "aws_pinpoint_sms_voice_v2_pool_origination_identity" "phone_pool_association" {
  count                     = var.enable_aws_sms ? 1 : 0
  pool_id                   = aws_pinpoint_sms_voice_v2_phone_pool.ai_nutritionist_pool[0].pool_id
  origination_identity_arn  = aws_pinpoint_sms_voice_v2_phone_number.ai_nutritionist_number[0].arn
  iso_country_code         = var.sms_phone_country
}

# CloudWatch Alarms for SMS monitoring
resource "aws_cloudwatch_metric_alarm" "sms_delivery_failure_rate" {
  count               = var.enable_aws_sms && var.enable_monitoring ? 1 : 0
  alarm_name          = "${var.project_name}-${var.environment}-sms-failure-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "TextMessageDeliveryFailureRate"
  namespace           = "AWS/SMS"
  period              = "300"
  statistic           = "Average"
  threshold           = "10"
  alarm_description   = "This metric monitors SMS delivery failure rate"
  alarm_actions       = var.enable_sns_alerts ? [aws_sns_topic.alerts[0].arn] : []
  
  dimensions = {
    ConfigurationSet = aws_pinpoint_sms_voice_v2_configuration_set.ai_nutritionist_config[0].name
  }
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-sms-failure-alarm"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_cloudwatch_metric_alarm" "inbound_sms_queue_depth" {
  count               = var.enable_aws_sms && var.enable_monitoring ? 1 : 0
  alarm_name          = "${var.project_name}-${var.environment}-inbound-sms-queue-depth"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ApproximateNumberOfVisibleMessages"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Average"
  threshold           = "100"
  alarm_description   = "This metric monitors inbound SMS queue depth"
  alarm_actions       = var.enable_sns_alerts ? [aws_sns_topic.alerts[0].arn] : []
  
  dimensions = {
    QueueName = aws_sqs_queue.inbound_sms[0].name
  }
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-sms-queue-alarm"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Note: API Gateway integration can be added if needed by extending existing API Gateway setup
# See api_gateway.tf for main API configuration
