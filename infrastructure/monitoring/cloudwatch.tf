# CloudWatch Comprehensive Monitoring Configuration

# Log Groups
resource "aws_cloudwatch_log_group" "lambda_logs" {
  for_each = var.lambda_functions
  
  name              = "/aws/lambda/${each.value}"
  retention_in_days = var.log_retention_days
  
  tags = merge(var.common_tags, {
    Name = "${each.value}-logs"
    Type = "lambda-logs"
  })
}

resource "aws_cloudwatch_log_group" "application_logs" {
  name              = "/ai-nutritionist/application"
  retention_in_days = var.log_retention_days
  
  tags = merge(var.common_tags, {
    Name = "application-logs"
    Type = "application-logs"
  })
}

resource "aws_cloudwatch_log_group" "security_logs" {
  name              = "/ai-nutritionist/security"
  retention_in_days = 365  # Keep security logs longer
  
  tags = merge(var.common_tags, {
    Name = "security-logs"
    Type = "security-logs"
  })
}

resource "aws_cloudwatch_log_group" "performance_logs" {
  name              = "/ai-nutritionist/performance"
  retention_in_days = var.log_retention_days
  
  tags = merge(var.common_tags, {
    Name = "performance-logs"
    Type = "performance-logs"
  })
}

# Custom Metrics
resource "aws_cloudwatch_log_metric_filter" "error_rate" {
  name           = "error-rate"
  log_group_name = aws_cloudwatch_log_group.application_logs.name
  pattern        = "[timestamp, request_id, level=\"ERROR\", ...]"
  
  metric_transformation {
    name      = "ErrorRate"
    namespace = "AI-Nutritionist/Application"
    value     = "1"
  }
}

resource "aws_cloudwatch_log_metric_filter" "response_time" {
  name           = "response-time"
  log_group_name = aws_cloudwatch_log_group.performance_logs.name
  pattern        = "[timestamp, request_id, response_time, ...]"
  
  metric_transformation {
    name      = "ResponseTime"
    namespace = "AI-Nutritionist/Performance"
    value     = "$response_time"
  }
}

resource "aws_cloudwatch_log_metric_filter" "business_metrics" {
  name           = "meal-plans-generated"
  log_group_name = aws_cloudwatch_log_group.application_logs.name
  pattern        = "[timestamp, request_id, event=\"MEAL_PLAN_GENERATED\", user_id, ...]"
  
  metric_transformation {
    name      = "MealPlansGenerated"
    namespace = "AI-Nutritionist/Business"
    value     = "1"
  }
}

resource "aws_cloudwatch_log_metric_filter" "revenue_metrics" {
  name           = "subscription-events"
  log_group_name = aws_cloudwatch_log_group.application_logs.name
  pattern        = "[timestamp, request_id, event=\"SUBSCRIPTION_EVENT\", amount, ...]"
  
  metric_transformation {
    name      = "Revenue"
    namespace = "AI-Nutritionist/Business"
    value     = "$amount"
  }
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "high_error_rate" {
  alarm_name          = "high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ErrorRate"
  namespace           = "AI-Nutritionist/Application"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors application error rate"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
  
  tags = var.common_tags
}

resource "aws_cloudwatch_metric_alarm" "high_response_time" {
  alarm_name          = "high-response-time"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ResponseTime"
  namespace           = "AI-Nutritionist/Performance"
  period              = "300"
  statistic           = "Average"
  threshold           = "5000"  # 5 seconds
  alarm_description   = "This metric monitors application response time"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  tags = var.common_tags
}

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each = var.lambda_functions
  
  alarm_name          = "${each.key}-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors ${each.key} lambda errors"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    FunctionName = each.value
  }
  
  tags = var.common_tags
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  for_each = var.lambda_functions
  
  alarm_name          = "${each.key}-lambda-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = "30000"  # 30 seconds
  alarm_description   = "This metric monitors ${each.key} lambda duration"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    FunctionName = each.value
  }
  
  tags = var.common_tags
}

resource "aws_cloudwatch_metric_alarm" "dynamodb_throttles" {
  for_each = var.dynamodb_tables
  
  alarm_name          = "${each.key}-dynamodb-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "UserErrors"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors ${each.key} DynamoDB throttles"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    TableName = each.value
  }
  
  tags = var.common_tags
}

# Business Metric Alarms
resource "aws_cloudwatch_metric_alarm" "low_conversion_rate" {
  alarm_name          = "low-conversion-rate"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "ConversionRate"
  namespace           = "AI-Nutritionist/Business"
  period              = "3600"  # 1 hour
  statistic           = "Average"
  threshold           = "0.02"  # 2%
  alarm_description   = "This metric monitors conversion rate"
  alarm_actions       = [aws_sns_topic.business_alerts.arn]
  
  tags = var.common_tags
}

resource "aws_cloudwatch_metric_alarm" "revenue_drop" {
  alarm_name          = "revenue-drop"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Revenue"
  namespace           = "AI-Nutritionist/Business"
  period              = "3600"  # 1 hour
  statistic           = "Sum"
  threshold           = "50"  # $50/hour minimum
  alarm_description   = "This metric monitors hourly revenue"
  alarm_actions       = [aws_sns_topic.business_alerts.arn]
  
  tags = var.common_tags
}

# SNS Topics for Alerts
resource "aws_sns_topic" "alerts" {
  name = "ai-nutritionist-alerts"
  
  tags = var.common_tags
}

resource "aws_sns_topic" "business_alerts" {
  name = "ai-nutritionist-business-alerts"
  
  tags = var.common_tags
}

# SNS Topic Subscriptions
resource "aws_sns_topic_subscription" "email_alerts" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_sns_topic_subscription" "business_email_alerts" {
  topic_arn = aws_sns_topic.business_alerts.arn
  protocol  = "email"
  endpoint  = var.business_alert_email
}

# PagerDuty Integration (if enabled)
resource "aws_sns_topic_subscription" "pagerduty" {
  count = var.enable_pagerduty ? 1 : 0
  
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "https"
  endpoint  = var.pagerduty_endpoint
}

# CloudWatch Insights Saved Queries
resource "aws_cloudwatch_query_definition" "error_analysis" {
  name = "AI-Nutritionist-Error-Analysis"
  
  log_group_names = [
    aws_cloudwatch_log_group.application_logs.name,
    aws_cloudwatch_log_group.lambda_logs["message_handler"].name
  ]
  
  query_string = <<EOF
fields @timestamp, @message, level, error, stack_trace
| filter level = "ERROR"
| sort @timestamp desc
| limit 100
EOF
}

resource "aws_cloudwatch_query_definition" "performance_analysis" {
  name = "AI-Nutritionist-Performance-Analysis"
  
  log_group_names = [
    aws_cloudwatch_log_group.performance_logs.name
  ]
  
  query_string = <<EOF
fields @timestamp, operation, response_time, cache_hit, cost
| filter response_time > 3000
| stats avg(response_time), max(response_time), count() by operation
| sort avg(response_time) desc
EOF
}

resource "aws_cloudwatch_query_definition" "business_metrics" {
  name = "AI-Nutritionist-Business-Metrics"
  
  log_group_names = [
    aws_cloudwatch_log_group.application_logs.name
  ]
  
  query_string = <<EOF
fields @timestamp, event, user_id, amount, subscription_tier
| filter event in ["SUBSCRIPTION_EVENT", "MEAL_PLAN_GENERATED", "USER_REGISTERED"]
| stats count() by event, bin(5m)
| sort @timestamp desc
EOF
}

# Outputs
output "cloudwatch_log_groups" {
  description = "CloudWatch log groups"
  value = {
    application = aws_cloudwatch_log_group.application_logs.name
    performance = aws_cloudwatch_log_group.performance_logs.name
    security    = aws_cloudwatch_log_group.security_logs.name
    lambda      = { for k, v in aws_cloudwatch_log_group.lambda_logs : k => v.name }
  }
}

output "sns_topics" {
  description = "SNS topics for alerts"
  value = {
    alerts          = aws_sns_topic.alerts.arn
    business_alerts = aws_sns_topic.business_alerts.arn
  }
}
