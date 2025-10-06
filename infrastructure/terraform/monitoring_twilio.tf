## Custom metrics alarms for external messaging providers (Twilio/WhatsApp Cloud)

resource "aws_cloudwatch_metric_alarm" "twilio_message_failure" {
  count               = var.enable_monitoring ? 1 : 0
  alarm_name          = "${var.project_name}-${var.environment}-twilio-message-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MessageFailed"
  namespace           = "AI-Nutritionist/Messaging"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "Twilio message failures exceed threshold"
  alarm_actions       = var.enable_sns_alerts ? [aws_sns_topic.alerts[0].arn] : []

  dimensions = {
    Provider = "Twilio"
  }
}

resource "aws_cloudwatch_metric_alarm" "whatsapp_cloud_message_failure" {
  count               = var.enable_monitoring ? 1 : 0
  alarm_name          = "${var.project_name}-${var.environment}-whatsapp-cloud-message-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MessageFailed"
  namespace           = "AI-Nutritionist/Messaging"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "WhatsApp Cloud message failures exceed threshold"
  alarm_actions       = var.enable_sns_alerts ? [aws_sns_topic.alerts[0].arn] : []

  dimensions = {
    Provider = "WhatsAppCloud"
  }
}

