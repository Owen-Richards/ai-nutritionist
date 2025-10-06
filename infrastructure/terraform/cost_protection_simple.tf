# 💰 SIMPLIFIED COST PROTECTION (Fixed for Terraform)
# Using only standard AWS provider resources

# ===== CLOUDWATCH BILLING ALERTS =====

# Enable billing alerts (prerequisite)
resource "aws_billing_metric" "main" {
  count = var.enable_billing_alerts ? 1 : 0
}

# Monthly budget alarm - 80% warning
resource "aws_cloudwatch_metric_alarm" "monthly_budget_warning" {
  alarm_name          = "${var.project_name}-budget-warning-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = "86400"  # 24 hours
  statistic           = "Maximum"
  threshold           = var.monthly_budget_hard_cap * 0.8
  alarm_description   = "Monthly budget warning at 80%"
  alarm_actions       = [aws_sns_topic.budget_alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    Currency = "USD"
  }

  tags = merge(
    {
      Name    = "${var.project_name}-budget-warning-${var.environment}"
      Purpose = "Budget warning alert"
    },
    var.additional_tags
  )
}

# Emergency budget alarm - 95% shutdown
resource "aws_cloudwatch_metric_alarm" "emergency_budget" {
  count               = var.enable_emergency_shutdown ? 1 : 0
  alarm_name          = "${var.project_name}-emergency-budget-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = "21600"  # 6 hours
  statistic           = "Maximum"
  threshold           = var.monthly_budget_hard_cap * 0.95
  alarm_description   = "EMERGENCY: Budget at 95% - triggering shutdown"
  alarm_actions       = [aws_sns_topic.emergency_shutdown.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    Currency = "USD"
  }

  tags = merge(
    {
      Name    = "${var.project_name}-emergency-budget-${var.environment}"
      Purpose = "Emergency budget protection"
    },
    var.additional_tags
  )
}

# Daily spending alarm
resource "aws_cloudwatch_metric_alarm" "daily_spending" {
  alarm_name          = "${var.project_name}-daily-spending-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = "86400"  # 24 hours
  statistic           = "Maximum"
  threshold           = var.daily_budget_limit
  alarm_description   = "Daily spending limit exceeded"
  alarm_actions       = [aws_sns_topic.daily_limit_exceeded.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    Currency = "USD"
  }

  tags = merge(
    {
      Name    = "${var.project_name}-daily-spending-${var.environment}"
      Purpose = "Daily spending monitoring"
    },
    var.additional_tags
  )
}

# ===== SNS TOPICS FOR ALERTS =====

resource "aws_sns_topic" "budget_alerts" {
  name         = "${var.project_name}-budget-alerts-${var.environment}"
  display_name = "Budget Alerts"

  tags = merge(
    {
      Name    = "${var.project_name}-budget-alerts-${var.environment}"
      Purpose = "Budget alert notifications"
    },
    var.additional_tags
  )
}

resource "aws_sns_topic" "emergency_shutdown" {
  name         = "${var.project_name}-emergency-shutdown-${var.environment}"
  display_name = "Emergency Budget Shutdown"

  tags = merge(
    {
      Name    = "${var.project_name}-emergency-shutdown-${var.environment}"
      Purpose = "Emergency shutdown notifications"
    },
    var.additional_tags
  )
}

resource "aws_sns_topic" "daily_limit_exceeded" {
  name         = "${var.project_name}-daily-limit-${var.environment}"
  display_name = "Daily Budget Limit"

  tags = merge(
    {
      Name    = "${var.project_name}-daily-limit-${var.environment}"
      Purpose = "Daily limit notifications"
    },
    var.additional_tags
  )
}

# ===== EMAIL SUBSCRIPTIONS =====

resource "aws_sns_topic_subscription" "budget_email" {
  topic_arn = aws_sns_topic.budget_alerts.arn
  protocol  = "email"
  endpoint  = var.owner_email
}

resource "aws_sns_topic_subscription" "emergency_email" {
  topic_arn = aws_sns_topic.emergency_shutdown.arn
  protocol  = "email"
  endpoint  = var.owner_email
}

resource "aws_sns_topic_subscription" "daily_limit_email" {
  topic_arn = aws_sns_topic.daily_limit_exceeded.arn
  protocol  = "email"
  endpoint  = var.owner_email
}

# ===== LAMBDA CONCURRENCY CONTROL =====
# Note: Lambda concurrency limits will be applied to existing Lambda functions
# via the main lambda.tf configuration

# ===== OUTPUTS FOR COST MONITORING =====

output "cost_protection_summary" {
  description = "Summary of cost protection measures"
  value = {
    monthly_budget_cap     = var.monthly_budget_hard_cap
    daily_budget_limit     = var.daily_budget_limit
    emergency_shutdown     = var.enable_emergency_shutdown
    testing_mode          = var.testing_mode
    lambda_concurrency_limit = var.lambda_concurrency_limit
    alert_email           = var.owner_email
    budget_alarm_arn      = aws_cloudwatch_metric_alarm.monthly_budget_warning.arn
    emergency_alarm_arn   = var.enable_emergency_shutdown ? aws_cloudwatch_metric_alarm.emergency_budget[0].arn : null
  }
}

output "alert_topic_arns" {
  description = "SNS topic ARNs for budget alerts"
  value = {
    budget_alerts      = aws_sns_topic.budget_alerts.arn
    emergency_shutdown = aws_sns_topic.emergency_shutdown.arn
    daily_limit        = aws_sns_topic.daily_limit_exceeded.arn
  }
}
