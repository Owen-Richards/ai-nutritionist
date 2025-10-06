# CloudWatch Dashboard for Monitoring
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-dashboard-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      # Lambda Functions Metrics
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.universal_message_handler.function_name],
            [".", "Errors", ".", "."],
            [".", "Invocations", ".", "."],
            [".", "Duration", "FunctionName", aws_lambda_function.billing_handler.function_name],
            [".", "Errors", ".", "."],
            [".", "Invocations", ".", "."],
            [".", "Duration", "FunctionName", aws_lambda_function.scheduler_handler.function_name],
            [".", "Errors", ".", "."],
            [".", "Invocations", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Lambda Function Metrics"
          period  = 300
        }
      },
      # DynamoDB Metrics
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", aws_dynamodb_table.user_data.name],
            [".", "ConsumedWriteCapacityUnits", ".", "."],
            [".", "ConsumedReadCapacityUnits", "TableName", aws_dynamodb_table.subscriptions.name],
            [".", "ConsumedWriteCapacityUnits", ".", "."],
            [".", "ConsumedReadCapacityUnits", "TableName", aws_dynamodb_table.usage.name],
            [".", "ConsumedWriteCapacityUnits", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "DynamoDB Capacity Metrics"
          period  = 300
        }
      },
      # API Gateway Metrics
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiName", aws_api_gateway_rest_api.main.name],
            [".", "Latency", ".", "."],
            [".", "4XXError", ".", "."],
            [".", "5XXError", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "API Gateway Metrics"
          period  = 300
        }
      },
      # CloudFront Metrics
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/CloudFront", "Requests", "DistributionId", aws_cloudfront_distribution.web_frontend.id],
            [".", "BytesDownloaded", ".", "."],
            [".", "4xxErrorRate", ".", "."],
            [".", "5xxErrorRate", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-east-1"  # CloudFront metrics are only in us-east-1
          title   = "CloudFront Metrics"
          period  = 300
        }
      },
      # Cost Optimization - Bedrock Usage
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 24
        height = 6

        properties = {
          metrics = [
            ["AWS/Bedrock", "InvocationsCount", "ModelId", var.bedrock_models[0]],
            [".", "InputTokenCount", ".", "."],
            [".", "OutputTokenCount", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Bedrock AI Usage and Cost Metrics"
          period  = 300
        }
      },
      # Messaging Providers - Custom Metrics
      {
        type   = "metric"
        x      = 0
        y      = 18
        width  = 24
        height = 6

        properties = {
          metrics = [
            ["AI-Nutritionist/Messaging", "MessageSent", "Provider", "Twilio"],
            [".", "MessageFailed", "Provider", "Twilio"],
            ["AI-Nutritionist/Messaging", "MessageSent", "Provider", "WhatsAppCloud"],
            [".", "MessageFailed", "Provider", "WhatsAppCloud"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Messaging Providers (Sent/Failed)"
          period  = 300
        }
      },
      # Messaging Cost per Provider (estimated)
      {
        type   = "metric"
        x      = 0
        y      = 24
        width  = 24
        height = 6

        properties = {
          metrics = [
            [{
              expression = "m1*0.0070"
              label      = "Twilio Cost (est USD)"
              id         = "e1"
            }],
            ["AI-Nutritionist/Messaging", "MessageSent", "Provider", "Twilio", {
              id   = "m1"
              stat = "Sum"
            }],
            [{
              expression = "m2*0.0050"
              label      = "WhatsApp Cloud Cost (est USD)"
              id         = "e2"
            }],
            ["AI-Nutritionist/Messaging", "MessageSent", "Provider", "WhatsAppCloud", {
              id   = "m2"
              stat = "Sum"
            }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Messaging Cost by Provider"
          period  = 300
        }
      }
    ]
  })
}

# CloudWatch Alarms for Lambda Functions
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each = {
    universal_message_handler = aws_lambda_function.universal_message_handler.function_name
    billing_handler          = aws_lambda_function.billing_handler.function_name
    scheduler_handler        = aws_lambda_function.scheduler_handler.function_name
  }

  alarm_name          = "${var.project_name}-lambda-errors-${each.key}-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors lambda errors for ${each.key}"
  alarm_actions       = var.enable_sns_alerts ? [aws_sns_topic.alerts[0].arn] : []

  dimensions = {
    FunctionName = each.value
  }

  tags = merge(
    {
      Name = "${var.project_name}-lambda-errors-${each.key}-${var.environment}"
    },
    var.additional_tags
  )
}

# CloudWatch Alarms for Lambda Duration
resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  for_each = {
    universal_message_handler = aws_lambda_function.universal_message_handler.function_name
    billing_handler          = aws_lambda_function.billing_handler.function_name
    scheduler_handler        = aws_lambda_function.scheduler_handler.function_name
  }

  alarm_name          = "${var.project_name}-lambda-duration-${each.key}-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = each.key == "billing_handler" ? "25000" : "25000"  # 25 seconds
  alarm_description   = "This metric monitors lambda duration for ${each.key}"
  alarm_actions       = var.enable_sns_alerts ? [aws_sns_topic.alerts[0].arn] : []

  dimensions = {
    FunctionName = each.value
  }

  tags = merge(
    {
      Name = "${var.project_name}-lambda-duration-${each.key}-${var.environment}"
    },
    var.additional_tags
  )
}

# CloudWatch Alarm for DynamoDB Throttling
resource "aws_cloudwatch_metric_alarm" "dynamodb_throttles" {
  for_each = {
    user_data     = aws_dynamodb_table.user_data.name
    subscriptions = aws_dynamodb_table.subscriptions.name
    usage         = aws_dynamodb_table.usage.name
    prompt_cache  = aws_dynamodb_table.prompt_cache.name
  }

  alarm_name          = "${var.project_name}-dynamodb-throttles-${each.key}-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ThrottledRequests"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors DynamoDB throttling for ${each.key}"
  alarm_actions       = var.enable_sns_alerts ? [aws_sns_topic.alerts[0].arn] : []

  dimensions = {
    TableName = each.value
  }

  tags = merge(
    {
      Name = "${var.project_name}-dynamodb-throttles-${each.key}-${var.environment}"
    },
    var.additional_tags
  )
}

# CloudWatch Alarm for API Gateway 5XX Errors
resource "aws_cloudwatch_metric_alarm" "api_gateway_5xx" {
  alarm_name          = "${var.project_name}-api-gateway-5xx-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors API Gateway 5XX errors"
  alarm_actions       = var.enable_sns_alerts ? [aws_sns_topic.alerts[0].arn] : []

  dimensions = {
    ApiName = aws_api_gateway_rest_api.main.name
  }

  tags = merge(
    {
      Name = "${var.project_name}-api-gateway-5xx-${var.environment}"
    },
    var.additional_tags
  )
}

# SNS Topic for Alerts (optional)
resource "aws_sns_topic" "alerts" {
  count = var.enable_sns_alerts ? 1 : 0
  
  name         = "${var.project_name}-alerts-${var.environment}"
  display_name = "AI Nutritionist Alerts"

  kms_master_key_id = aws_kms_key.cloudwatch.arn

  tags = merge(
    {
      Name = "${var.project_name}-alerts-${var.environment}"
    },
    var.additional_tags
  )
}

# SNS Topic Subscription (optional)
resource "aws_sns_topic_subscription" "email_alerts" {
  count = var.enable_sns_alerts && var.alert_email != "" ? 1 : 0
  
  topic_arn = aws_sns_topic.alerts[0].arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Cost Budget using CloudWatch Alarms (simpler than AWS Budgets)
resource "aws_cloudwatch_metric_alarm" "monthly_cost_budget" {
  count = var.enable_cost_budgets ? 1 : 0
  
  alarm_name          = "${var.project_name}-monthly-budget-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = "86400"  # 24 hours
  statistic           = "Maximum"
  threshold           = var.monthly_budget_limit
  alarm_description   = "Monthly budget threshold exceeded"
  alarm_actions       = var.enable_sns_alerts ? [aws_sns_topic.alerts[0].arn] : []
  treat_missing_data  = "notBreaching"

  dimensions = {
    Currency = "USD"
  }

  tags = merge(
    {
      Name    = "${var.project_name}-monthly-budget-${var.environment}"
      Purpose = "Monthly cost monitoring"
    },
    var.additional_tags
  )
}

# CloudWatch Insights Saved Queries for Troubleshooting
resource "aws_cloudwatch_query_definition" "lambda_errors" {
  name = "${var.project_name}-lambda-errors-${var.environment}"

  log_group_names = [
    aws_cloudwatch_log_group.lambda_universal_message_handler.name,
    aws_cloudwatch_log_group.lambda_billing_handler.name,
    aws_cloudwatch_log_group.lambda_scheduler_handler.name
  ]

  query_string = <<-EOT
    fields @timestamp, @message
    | filter @message like /ERROR/
    | sort @timestamp desc
    | limit 20
  EOT
}

resource "aws_cloudwatch_query_definition" "slow_requests" {
  name = "${var.project_name}-slow-requests-${var.environment}"

  log_group_names = [
    aws_cloudwatch_log_group.lambda_universal_message_handler.name
  ]

  query_string = <<-EOT
    fields @timestamp, @duration, @message
    | filter @type = "REPORT"
    | filter @duration > 10000
    | sort @timestamp desc
    | limit 20
  EOT
}

# Cost Anomaly Detection using CloudWatch Composite Alarms (simpler approach)
resource "aws_cloudwatch_composite_alarm" "cost_anomaly_detector" {
  count = var.enable_cost_anomaly_detection ? 1 : 0
  
  alarm_name        = "${var.project_name}-cost-anomaly-${var.environment}"
  alarm_description = "Detects unusual spending patterns"
  
  alarm_rule = "ALARM(${aws_cloudwatch_metric_alarm.monthly_cost_budget[0].alarm_name})"
  
  actions_enabled = true
  alarm_actions   = var.enable_sns_alerts ? [aws_sns_topic.alerts[0].arn] : []

  tags = merge(
    {
      Name    = "${var.project_name}-cost-anomaly-${var.environment}"
      Purpose = "Cost anomaly detection"
    },
    var.additional_tags
  )
}
