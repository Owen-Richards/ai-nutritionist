# AWS SMS Spam Protection and Cost Controls
# Advanced protection against spam, abuse, and cost overruns

# DynamoDB table for rate limiting and user tracking
resource "aws_dynamodb_table" "sms_rate_limits" {
  count          = var.enable_aws_sms ? 1 : 0
  name           = "${var.project_name}-${var.environment}-sms-rate-limits"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "phone_number"
  
  attribute {
    name = "phone_number"
    type = "S"
  }
  
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-sms-rate-limits"
    Environment = var.environment
    Project     = var.project_name
  }
}

# DynamoDB table for spam detection and user reputation
resource "aws_dynamodb_table" "user_reputation" {
  count          = var.enable_aws_sms ? 1 : 0
  name           = "${var.project_name}-${var.environment}-user-reputation"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "phone_number"
  
  attribute {
    name = "phone_number"
    type = "S"
  }
  
  attribute {
    name = "last_activity"
    type = "N"
  }
  
  global_secondary_index {
    name     = "LastActivityIndex"
    hash_key = "last_activity"
  }
  
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-user-reputation"
    Environment = var.environment
    Project     = var.project_name
  }
}

# DynamoDB table for blocked numbers and spam patterns
resource "aws_dynamodb_table" "blocked_numbers" {
  count          = var.enable_aws_sms ? 1 : 0
  name           = "${var.project_name}-${var.environment}-blocked-numbers"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "phone_number"
  
  attribute {
    name = "phone_number"
    type = "S"
  }
  
  attribute {
    name = "block_reason"
    type = "S"
  }
  
  global_secondary_index {
    name     = "BlockReasonIndex"
    hash_key = "block_reason"
  }
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-blocked-numbers"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Lambda function for spam detection and rate limiting
resource "aws_lambda_function" "spam_protection" {
  count           = var.enable_aws_sms ? 1 : 0
  filename        = "lambda_functions.zip"
  function_name   = "${var.project_name}-${var.environment}-spam-protection"
  role           = aws_iam_role.spam_protection_lambda_role[0].arn
  handler        = "handlers.spam_protection_handler.lambda_handler"
  runtime        = var.lambda_runtime
  timeout        = 30
  memory_size    = 512
  
  environment {
    variables = {
      RATE_LIMITS_TABLE    = aws_dynamodb_table.sms_rate_limits[0].name
      USER_REPUTATION_TABLE = aws_dynamodb_table.user_reputation[0].name
      BLOCKED_NUMBERS_TABLE = aws_dynamodb_table.blocked_numbers[0].name
      MAX_MESSAGES_PER_HOUR = var.max_messages_per_hour
      MAX_MESSAGES_PER_DAY  = var.max_messages_per_day
      DAILY_COST_LIMIT     = var.daily_cost_limit
      ENVIRONMENT          = var.environment
    }
  }
  
  depends_on = [
    aws_iam_role_policy_attachment.spam_protection_lambda_policy,
    aws_cloudwatch_log_group.spam_protection_lambda_logs,
  ]
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-spam-protection"
    Environment = var.environment
    Project     = var.project_name
  }
}

# CloudWatch Log Group for spam protection Lambda
resource "aws_cloudwatch_log_group" "spam_protection_lambda_logs" {
  count             = var.enable_aws_sms ? 1 : 0
  name              = "/aws/lambda/${var.project_name}-${var.environment}-spam-protection"
  retention_in_days = 14
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-spam-protection-logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

# IAM Role for spam protection Lambda
resource "aws_iam_role" "spam_protection_lambda_role" {
  count = var.enable_aws_sms ? 1 : 0
  name  = "${var.project_name}-${var.environment}-spam-protection-lambda-role"
  
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
    Name        = "${var.project_name}-${var.environment}-spam-protection-lambda-role"
    Environment = var.environment
    Project     = var.project_name
  }
}

# IAM Policy for spam protection Lambda
resource "aws_iam_role_policy" "spam_protection_lambda_policy" {
  count = var.enable_aws_sms ? 1 : 0
  name  = "${var.project_name}-${var.environment}-spam-protection-lambda-policy"
  role  = aws_iam_role.spam_protection_lambda_role[0].id
  
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
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:DeleteItem"
        ]
        Resource = [
          aws_dynamodb_table.sms_rate_limits[0].arn,
          aws_dynamodb_table.user_reputation[0].arn,
          aws_dynamodb_table.blocked_numbers[0].arn,
          "${aws_dynamodb_table.sms_rate_limits[0].arn}/index/*",
          "${aws_dynamodb_table.user_reputation[0].arn}/index/*",
          "${aws_dynamodb_table.blocked_numbers[0].arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sms-voice:PutOptedOutNumber",
          "sms-voice:DeleteOptedOutNumber"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach basic execution policy
resource "aws_iam_role_policy_attachment" "spam_protection_lambda_policy" {
  count      = var.enable_aws_sms ? 1 : 0
  role       = aws_iam_role.spam_protection_lambda_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# CloudWatch Alarms for cost and spam monitoring
resource "aws_cloudwatch_metric_alarm" "daily_cost_limit" {
  count               = var.enable_aws_sms && var.enable_monitoring ? 1 : 0
  alarm_name          = "${var.project_name}-${var.environment}-daily-cost-limit"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = "86400"  # 24 hours
  statistic           = "Maximum"
  threshold           = var.daily_cost_limit
  alarm_description   = "Daily SMS cost limit exceeded"
  alarm_actions       = var.enable_sns_alerts ? [aws_sns_topic.alerts[0].arn] : []
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    Currency = "USD"
    ServiceName = "AmazonPinpoint"
  }
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-cost-alarm"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_cloudwatch_metric_alarm" "high_message_volume" {
  count               = var.enable_aws_sms && var.enable_monitoring ? 1 : 0
  alarm_name          = "${var.project_name}-${var.environment}-high-message-volume"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "NumberOfMessagesReceived"
  namespace           = "AWS/SQS"
  period              = "300"  # 5 minutes
  statistic           = "Sum"
  threshold           = var.max_messages_per_hour / 12  # Per 5-minute period
  alarm_description   = "Unusually high message volume detected"
  alarm_actions       = var.enable_sns_alerts ? [aws_sns_topic.alerts[0].arn] : []
  
  dimensions = {
    QueueName = aws_sqs_queue.inbound_sms[0].name
  }
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-volume-alarm"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_cloudwatch_metric_alarm" "spam_detection_rate" {
  count               = var.enable_aws_sms && var.enable_monitoring ? 1 : 0
  alarm_name          = "${var.project_name}-${var.environment}-spam-detection-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "SpamMessagesDetected"
  namespace           = "AI-Nutritionist/SMS"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "High spam detection rate"
  alarm_actions       = var.enable_sns_alerts ? [aws_sns_topic.alerts[0].arn] : []
  treat_missing_data  = "notBreaching"
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-spam-alarm"
    Environment = var.environment
    Project     = var.project_name
  }
}

# EventBridge rule for automated cost monitoring
resource "aws_cloudwatch_event_rule" "daily_cost_check" {
  count               = var.enable_aws_sms ? 1 : 0
  name                = "${var.project_name}-${var.environment}-daily-cost-check"
  description         = "Trigger daily cost analysis"
  schedule_expression = "cron(0 1 * * ? *)"  # Daily at 1 AM UTC
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-cost-check"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_cloudwatch_event_target" "daily_cost_check_target" {
  count     = var.enable_aws_sms ? 1 : 0
  rule      = aws_cloudwatch_event_rule.daily_cost_check[0].name
  target_id = "SpamProtectionTarget"
  arn       = aws_lambda_function.spam_protection[0].arn
  
  input = jsonencode({
    "action" = "daily_cost_analysis"
  })
}

resource "aws_lambda_permission" "allow_eventbridge_spam_protection" {
  count         = var.enable_aws_sms ? 1 : 0
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.spam_protection[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_cost_check[0].arn
}

# WAF Web ACL for additional protection (if using API Gateway)
resource "aws_wafv2_web_acl" "sms_protection" {
  count       = var.enable_aws_sms && var.enable_waf_protection ? 1 : 0
  name        = "${var.project_name}-${var.environment}-sms-waf"
  description = "WAF protection for SMS API endpoints"
  scope       = "REGIONAL"
  
  default_action {
    allow {}
  }
  
  # Rate limiting rule
  rule {
    name     = "RateLimitRule"
    priority = 1
    
    override_action {
      none {}
    }
    
    statement {
      rate_based_statement {
        limit              = var.waf_rate_limit
        aggregate_key_type = "IP"
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimitRule"
      sampled_requests_enabled   = true
    }
    
    action {
      block {}
    }
  }
  
  # Geographic restriction (optional)
  rule {
    name     = "GeoBlockRule"
    priority = 2
    
    override_action {
      none {}
    }
    
    statement {
      geo_match_statement {
        country_codes = var.blocked_countries
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "GeoBlockRule"
      sampled_requests_enabled   = true
    }
    
    action {
      block {}
    }
  }
  
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.project_name}-${var.environment}-sms-waf"
    sampled_requests_enabled   = true
  }
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-sms-waf"
    Environment = var.environment
    Project     = var.project_name
  }
}
