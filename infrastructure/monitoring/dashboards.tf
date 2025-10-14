# CloudWatch Dashboard Configuration

resource "aws_cloudwatch_dashboard" "main_dashboard" {
  dashboard_name = "AI-Nutritionist-Main-Dashboard"

  dashboard_body = jsonencode({
    widgets = [
      # Application Performance Overview
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AI-Nutritionist/Application", "ErrorRate"],
            ["AI-Nutritionist/Performance", "ResponseTime"],
            ["AI-Nutritionist/Application", "RequestCount"],
            ["AI-Nutritionist/Performance", "CacheHitRate"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Application Performance Overview"
          period  = 300
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },

      # Business Metrics
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AI-Nutritionist/Business", "MealPlansGenerated"],
            ["AI-Nutritionist/Business", "Revenue"],
            ["AI-Nutritionist/Business", "ConversionRate"],
            ["AI-Nutritionist/Business", "ActiveUsers"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Business Metrics"
          period  = 300
        }
      }
    ]
  })
}
