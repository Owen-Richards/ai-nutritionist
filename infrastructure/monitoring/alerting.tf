# Incident Response and Alerting Configuration

# PagerDuty Integration
resource "aws_sns_topic" "pagerduty_alerts" {
  count = var.enable_pagerduty ? 1 : 0
  name  = "ai-nutritionist-pagerduty-alerts"
  
  tags = var.common_tags
}

resource "aws_sns_topic_subscription" "pagerduty_critical" {
  count     = var.enable_pagerduty ? 1 : 0
  topic_arn = aws_sns_topic.pagerduty_alerts[0].arn
  protocol  = "https"
  endpoint  = var.pagerduty_endpoint
}

# Escalation Policy Configuration
locals {
  alert_escalation_matrix = {
    "low" = {
      notification_delay = 0
      escalation_delay   = 3600  # 1 hour
      sns_topic         = aws_sns_topic.alerts.arn
    }
    "medium" = {
      notification_delay = 0
      escalation_delay   = 1800  # 30 minutes
      sns_topic         = aws_sns_topic.alerts.arn
    }
    "high" = {
      notification_delay = 0
      escalation_delay   = 900   # 15 minutes
      sns_topic         = var.enable_pagerduty ? aws_sns_topic.pagerduty_alerts[0].arn : aws_sns_topic.alerts.arn
    }
    "critical" = {
      notification_delay = 0
      escalation_delay   = 300   # 5 minutes
      sns_topic         = var.enable_pagerduty ? aws_sns_topic.pagerduty_alerts[0].arn : aws_sns_topic.alerts.arn
    }
  }
}

# Critical Error Rate Alarm
resource "aws_cloudwatch_metric_alarm" "critical_error_rate" {
  alarm_name          = "critical-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ErrorRate"
  namespace           = "AI-Nutritionist/Application"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "Critical: High error rate detected - immediate action required"
  alarm_actions       = [local.alert_escalation_matrix.critical.sns_topic]
  ok_actions          = [local.alert_escalation_matrix.critical.sns_topic]
  treat_missing_data  = "breaching"
  
  tags = var.common_tags
}

# Performance Degradation Alarm
resource "aws_cloudwatch_metric_alarm" "performance_degradation" {
  alarm_name          = "performance-degradation"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "ResponseTime"
  namespace           = "AI-Nutritionist/Performance"
  period              = "300"
  statistic           = "Average"
  threshold           = "8000"  # 8 seconds
  alarm_description   = "High: Performance degradation detected"
  alarm_actions       = [local.alert_escalation_matrix.high.sns_topic]
  
  tags = var.common_tags
}

# Business Metric Anomaly Detection
resource "aws_cloudwatch_anomaly_detector" "revenue_anomaly" {
  metric_math_anomaly_detector {
    metric_data_queries {
      id          = "m1"
      return_data = true
      metric_stat {
        metric {
          metric_name = "Revenue"
          namespace   = "AI-Nutritionist/Business"
        }
        period = 3600
        stat   = "Sum"
      }
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "revenue_anomaly_alarm" {
  alarm_name          = "revenue-anomaly-detection"
  comparison_operator = "LessThanLowerOrGreaterThanUpperThreshold"
  evaluation_periods  = "2"
  threshold_metric_id = "ad1"
  alarm_description   = "Revenue anomaly detected - investigate business metrics"
  alarm_actions       = [aws_sns_topic.business_alerts.arn]
  
  metric_query {
    id          = "ad1"
    return_data = true
    anomaly_detector {
      metric_math_anomaly_detector {
        metric_data_queries {
          id          = "m1"
          return_data = true
          metric_stat {
            metric {
              metric_name = "Revenue"
              namespace   = "AI-Nutritionist/Business"
            }
            period = 3600
            stat   = "Sum"
          }
        }
      }
    }
  }
  
  metric_query {
    id          = "m1"
    return_data = true
    metric_stat {
      metric {
        metric_name = "Revenue"
        namespace   = "AI-Nutritionist/Business"
      }
      period = 3600
      stat   = "Sum"
    }
  }
  
  tags = var.common_tags
}

# Composite Alarms for Complex Scenarios
resource "aws_cloudwatch_composite_alarm" "system_health_degradation" {
  alarm_name        = "system-health-degradation"
  alarm_description = "System health is degrading across multiple metrics"
  
  alarm_rule = "ALARM(${aws_cloudwatch_metric_alarm.high_error_rate.alarm_name}) OR ALARM(${aws_cloudwatch_metric_alarm.high_response_time.alarm_name})"
  
  actions_enabled = true
  alarm_actions   = [local.alert_escalation_matrix.high.sns_topic]
  ok_actions      = [local.alert_escalation_matrix.high.sns_topic]
  
  tags = var.common_tags
}

# Lambda Function Dead Letter Queue Alarms
resource "aws_cloudwatch_metric_alarm" "lambda_dlq_messages" {
  for_each = var.lambda_functions
  
  alarm_name          = "${each.key}-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ApproximateNumberOfMessages"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Messages in DLQ for ${each.key} function"
  alarm_actions       = [local.alert_escalation_matrix.high.sns_topic]
  
  dimensions = {
    QueueName = "${each.value}-dlq"
  }
  
  tags = var.common_tags
}

# Resource Utilization Alarms
resource "aws_cloudwatch_metric_alarm" "dynamodb_capacity_alarm" {
  for_each = var.dynamodb_tables
  
  alarm_name          = "${each.key}-capacity-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ConsumedReadCapacityUnits"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "80"  # 80% of provisioned capacity
  alarm_description   = "High capacity utilization for ${each.key} table"
  alarm_actions       = [local.alert_escalation_matrix.medium.sns_topic]
  
  dimensions = {
    TableName = each.value
  }
  
  tags = var.common_tags
}

# Cost Anomaly Detection
resource "aws_ce_anomaly_detector" "cost_anomaly" {
  name         = "ai-nutritionist-cost-anomaly"
  monitor_type = "DIMENSIONAL"

  specification = jsonencode({
    Dimension = {
      Key           = "SERVICE"
      Values        = ["Amazon DynamoDB", "AWS Lambda", "Amazon CloudWatch", "Amazon API Gateway"]
      MatchOptions  = ["EQUALS"]
    }
  })
  
  tags = var.common_tags
}

resource "aws_ce_anomaly_subscription" "cost_anomaly_subscription" {
  name      = "ai-nutritionist-cost-alerts"
  frequency = "DAILY"
  
  monitor_arn_list = [
    aws_ce_anomaly_detector.cost_anomaly.arn
  ]
  
  subscriber {
    type    = "EMAIL"
    address = var.business_alert_email
  }
  
  threshold_expression {
    and {
      dimension {
        key           = "ANOMALY_TOTAL_IMPACT_ABSOLUTE"
        values        = ["100"]
        match_options = ["GREATER_THAN_OR_EQUAL"]
      }
    }
  }
  
  tags = var.common_tags
}

# Custom EventBridge Rules for Application Events
resource "aws_cloudwatch_event_rule" "application_errors" {
  name        = "ai-nutritionist-application-errors"
  description = "Capture application error events"

  event_pattern = jsonencode({
    source      = ["ai-nutritionist"]
    detail-type = ["Application Error"]
    detail = {
      severity = ["HIGH", "CRITICAL"]
    }
  })
  
  tags = var.common_tags
}

resource "aws_cloudwatch_event_target" "application_errors_target" {
  rule      = aws_cloudwatch_event_rule.application_errors.name
  target_id = "SendToSNS"
  arn       = local.alert_escalation_matrix.high.sns_topic
}

# Scheduled Health Checks
resource "aws_cloudwatch_event_rule" "health_check_schedule" {
  name                = "ai-nutritionist-health-check"
  description         = "Trigger health check every 5 minutes"
  schedule_expression = "rate(5 minutes)"
  
  tags = var.common_tags
}

resource "aws_cloudwatch_event_target" "health_check_target" {
  rule      = aws_cloudwatch_event_rule.health_check_schedule.name
  target_id = "HealthCheckLambda"
  arn       = "arn:aws:lambda:${var.aws_region}:ACCOUNT_ID:function:ai-nutritionist-health-check"
}

# IAM Role for CloudWatch Events
resource "aws_iam_role" "cloudwatch_events_role" {
  name = "ai-nutritionist-cloudwatch-events-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })
  
  tags = var.common_tags
}

resource "aws_iam_role_policy" "cloudwatch_events_policy" {
  name = "ai-nutritionist-cloudwatch-events-policy"
  role = aws_iam_role.cloudwatch_events_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sns:Publish",
          "lambda:InvokeFunction"
        ]
        Resource = [
          aws_sns_topic.alerts.arn,
          aws_sns_topic.business_alerts.arn,
          "arn:aws:lambda:${var.aws_region}:*:function:ai-nutritionist-*"
        ]
      }
    ]
  })
}
