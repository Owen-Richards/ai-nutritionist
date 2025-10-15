# ===== COST MONITORING DASHBOARD =====

resource "aws_cloudwatch_dashboard" "cost_optimization" {
  dashboard_name = "${var.project_name}-cost-optimization-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      # Cost Overview
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Billing", "EstimatedCharges", "Currency", "USD", "ServiceName", "AWSLambda"],
            [".", ".", ".", ".", ".", "AmazonDynamoDB"],
            [".", ".", ".", ".", ".", "AmazonApiGateway"],
            [".", ".", ".", ".", ".", "AmazonCloudFront"],
            [".", ".", ".", ".", ".", "AmazonS3"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Daily Estimated Charges by Service"
          period  = 86400
          stat    = "Maximum"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      
      # Lambda Cost Efficiency
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.universal_message_handler.function_name],
            [".", "Invocations", ".", "."],
            [".", "Errors", ".", "."],
            [".", "Duration", "FunctionName", aws_lambda_function.billing_handler.function_name],
            [".", "Invocations", ".", "."],
            [".", "Duration", "FunctionName", aws_lambda_function.scheduler_handler.function_name],
            [".", "Invocations", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Lambda Performance Metrics (Cost Efficiency)"
          period  = 300
        }
      },
      
      # DynamoDB Capacity Utilization
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", aws_dynamodb_table.user_data.name],
            [".", "ProvisionedReadCapacityUnits", ".", "."],
            [".", "ConsumedWriteCapacityUnits", ".", "."],
            [".", "ProvisionedWriteCapacityUnits", ".", "."],
            [".", "ConsumedReadCapacityUnits", "TableName", aws_dynamodb_table.subscriptions.name],
            [".", "ProvisionedReadCapacityUnits", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "DynamoDB Capacity Utilization"
          period  = 300
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      
      # API Gateway Cost Metrics
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiName", aws_api_gateway_rest_api.main.name],
            [".", "CacheHitCount", ".", "."],
            [".", "CacheMissCount", ".", "."],
            [".", "Latency", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "API Gateway Usage and Caching"
          period  = 300
        }
      },
      
      # Cost Anomaly Detection
      {
        type   = "log"
        x      = 0
        y      = 12
        width  = 24
        height = 6

        properties = {
          query   = "SOURCE '/aws/lambda/${var.project_name}-cost-optimizer-${var.environment}' | fields @timestamp, @message | filter @message like /anomaly/ | sort @timestamp desc | limit 20"
          region  = var.aws_region
          title   = "Recent Cost Anomalies"
          view    = "table"
        }
      },
      
      # S3 Storage Classes
      {
        type   = "metric"
        x      = 0
        y      = 18
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/S3", "BucketSizeBytes", "BucketName", aws_s3_bucket.web_frontend.bucket, "StorageType", "StandardStorage"],
            [".", ".", ".", ".", ".", "StandardIAStorage"],
            [".", ".", ".", ".", ".", "GlacierStorage"],
            [".", "NumberOfObjects", ".", ".", ".", "AllStorageTypes"]
          ]
          view    = "timeSeries"
          stacked = true
          region  = var.aws_region
          title   = "S3 Storage Distribution (Cost Optimization)"
          period  = 86400
        }
      },
      
      # CloudFront Cost Efficiency
      {
        type   = "metric"
        x      = 12
        y      = 18
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/CloudFront", "Requests", "DistributionId", aws_cloudfront_distribution.web_frontend.id],
            [".", "BytesDownloaded", ".", "."],
            [".", "BytesUploaded", ".", "."],
            [".", "OriginLatency", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-east-1"
          title   = "CloudFront Performance and Cost"
          period  = 300
        }
      },
      
      # Resource Utilization Summary
      {
        type   = "number"
        x      = 0
        y      = 24
        width  = 6
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.universal_message_handler.function_name]
          ]
          view    = "singleValue"
          region  = var.aws_region
          title   = "Avg Lambda Duration"
          period  = 86400
          stat    = "Average"
        }
      },
      
      {
        type   = "number"
        x      = 6
        y      = 24
        width  = 6
        height = 6

        properties = {
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", aws_dynamodb_table.user_data.name]
          ]
          view    = "singleValue"
          region  = var.aws_region
          title   = "DynamoDB Read Usage"
          period  = 86400
          stat    = "Sum"
        }
      },
      
      {
        type   = "number"
        x      = 12
        y      = 24
        width  = 6
        height = 6

        properties = {
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiName", aws_api_gateway_rest_api.main.name]
          ]
          view    = "singleValue"
          region  = var.aws_region
          title   = "API Requests"
          period  = 86400
          stat    = "Sum"
        }
      },
      
      {
        type   = "number"
        x      = 18
        y      = 24
        width  = 6
        height = 6

        properties = {
          metrics = [
            ["AWS/Billing", "EstimatedCharges", "Currency", "USD"]
          ]
          view    = "singleValue"
          region  = var.aws_region
          title   = "Total Daily Cost"
          period  = 86400
          stat    = "Maximum"
        }
      }
    ]
  })

  tags = merge(local.cost_tags, {
    Name = "${var.project_name}-cost-optimization-dashboard-${var.environment}"
    Purpose = "Cost monitoring and optimization dashboard"
  })
}

# ===== COST OPTIMIZATION REPORTS =====

resource "aws_lambda_function" "cost_report_generator" {
  filename         = data.archive_file.cost_report_zip.output_path
  source_code_hash = data.archive_file.cost_report_zip.output_base64sha256
  function_name    = "${var.project_name}-cost-report-generator-${var.environment}"
  role            = aws_iam_role.cost_optimizer_role.arn
  handler         = "cost_report.lambda_handler"
  runtime         = "python3.11"
  timeout         = 600
  memory_size     = 512
  architectures   = ["arm64"]

  environment {
    variables = {
      ENVIRONMENT          = var.environment
      PROJECT_NAME         = var.project_name
      SNS_TOPIC_ARN       = aws_sns_topic.cost_alerts.arn
      S3_BUCKET           = aws_s3_bucket.web_frontend.bucket
      DASHBOARD_URL       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.cost_optimization.dashboard_name}"
      MONTHLY_BUDGET      = var.monthly_budget_limit
    }
  }

  tags = merge(local.cost_tags, {
    Name = "${var.project_name}-cost-report-generator-${var.environment}"
    Purpose = "Generate detailed cost reports and recommendations"
  })
}

data "archive_file" "cost_report_zip" {
  type        = "zip"
  output_path = "${path.module}/temp/cost_report.zip"
  
  source {
    content = <<-EOF
import json
import boto3
import os
from datetime import datetime, timedelta
import csv
from io import StringIO

def lambda_handler(event, context):
    """Generate comprehensive cost optimization report"""
    try:
        # Initialize clients
        ce_client = boto3.client('ce')
        s3_client = boto3.client('s3')
        sns_client = boto3.client('sns')
        
        # Generate cost analysis
        cost_data = get_detailed_cost_analysis(ce_client)
        
        # Generate recommendations
        recommendations = generate_detailed_recommendations(cost_data)
        
        # Create CSV report
        csv_content = create_csv_report(cost_data, recommendations)
        
        # Upload to S3
        report_key = f"cost-reports/{datetime.now().strftime('%Y-%m')}/cost-optimization-report-{datetime.now().strftime('%Y-%m-%d')}.csv"
        s3_client.put_object(
            Bucket=os.environ['S3_BUCKET'],
            Key=report_key,
            Body=csv_content,
            ContentType='text/csv'
        )
        
        # Generate summary email
        send_cost_summary_email(sns_client, cost_data, recommendations, report_key)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'report_generated': True,
                'report_location': f"s3://{os.environ['S3_BUCKET']}/{report_key}",
                'summary': cost_data['summary'],
                'recommendations_count': len(recommendations)
            })
        }
        
    except Exception as e:
        print(f"Error generating cost report: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def get_detailed_cost_analysis(ce_client):
    """Get detailed cost analysis for the past 30 days"""
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    # Get cost by service
    service_costs = ce_client.get_cost_and_usage(
        TimePeriod={'Start': start_date, 'End': end_date},
        Granularity='MONTHLY',
        Metrics=['BlendedCost'],
        GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
    )
    
    # Get daily costs for trend analysis
    daily_costs = ce_client.get_cost_and_usage(
        TimePeriod={'Start': start_date, 'End': end_date},
        Granularity='DAILY',
        Metrics=['BlendedCost']
    )
    
    # Process data
    services = {}
    total_cost = 0
    
    for result in service_costs['ResultsByTime']:
        for group in result['Groups']:
            service = group['Keys'][0] if group['Keys'] else 'Unknown'
            cost = float(group['Metrics']['BlendedCost']['Amount'])
            services[service] = cost
            total_cost += cost
    
    # Calculate daily trend
    daily_values = []
    for result in daily_costs['ResultsByTime']:
        daily_cost = float(result['Total']['BlendedCost']['Amount'])
        daily_values.append(daily_cost)
    
    # Calculate trend
    recent_avg = sum(daily_values[-7:]) / 7 if len(daily_values) >= 7 else 0
    previous_avg = sum(daily_values[-14:-7]) / 7 if len(daily_values) >= 14 else 0
    trend_percentage = ((recent_avg - previous_avg) / previous_avg * 100) if previous_avg > 0 else 0
    
    return {
        'total_30_day_cost': total_cost,
        'services': services,
        'daily_costs': daily_values,
        'recent_avg_daily': recent_avg,
        'trend_percentage': trend_percentage,
        'highest_cost_service': max(services.items(), key=lambda x: x[1]) if services else ('None', 0),
        'summary': {
            'total_cost': total_cost,
            'daily_average': recent_avg,
            'trend': 'increasing' if trend_percentage > 5 else 'decreasing' if trend_percentage < -5 else 'stable',
            'top_service': max(services.items(), key=lambda x: x[1])[0] if services else 'None'
        }
    }

def generate_detailed_recommendations(cost_data):
    """Generate detailed cost optimization recommendations"""
    recommendations = []
    
    # Lambda optimization
    lambda_cost = cost_data['services'].get('AWS Lambda', 0)
    if lambda_cost > 20:
        recommendations.append({
            'service': 'AWS Lambda',
            'current_cost': lambda_cost,
            'recommendation': 'Consider using ARM64 Graviton2 processors',
            'potential_savings': lambda_cost * 0.20,
            'implementation': 'Update Lambda architecture to arm64',
            'priority': 'High'
        })
    
    # DynamoDB optimization
    dynamodb_cost = cost_data['services'].get('Amazon DynamoDB', 0)
    if dynamodb_cost > 30:
        recommendations.append({
            'service': 'Amazon DynamoDB',
            'current_cost': dynamodb_cost,
            'recommendation': 'Enable on-demand billing for variable workloads',
            'potential_savings': dynamodb_cost * 0.25,
            'implementation': 'Switch to on-demand billing mode',
            'priority': 'Medium'
        })
    
    # API Gateway optimization
    api_cost = cost_data['services'].get('Amazon API Gateway', 0)
    if api_cost > 15:
        recommendations.append({
            'service': 'Amazon API Gateway',
            'current_cost': api_cost,
            'recommendation': 'Implement response caching',
            'potential_savings': api_cost * 0.30,
            'implementation': 'Enable API Gateway caching with 5-minute TTL',
            'priority': 'High'
        })
    
    # CloudFront optimization
    cloudfront_cost = cost_data['services'].get('Amazon CloudFront', 0)
    if cloudfront_cost > 10:
        recommendations.append({
            'service': 'Amazon CloudFront',
            'current_cost': cloudfront_cost,
            'recommendation': 'Use PriceClass_100 for regional distribution',
            'potential_savings': cloudfront_cost * 0.15,
            'implementation': 'Change CloudFront price class to PriceClass_100',
            'priority': 'Low'
        })
    
    # S3 optimization
    s3_cost = cost_data['services'].get('Amazon Simple Storage Service', 0)
    if s3_cost > 5:
        recommendations.append({
            'service': 'Amazon S3',
            'current_cost': s3_cost,
            'recommendation': 'Implement lifecycle policies for data archiving',
            'potential_savings': s3_cost * 0.40,
            'implementation': 'Move objects to IA after 30 days, Glacier after 90 days',
            'priority': 'Medium'
        })
    
    return recommendations

def create_csv_report(cost_data, recommendations):
    """Create CSV report content"""
    output = StringIO()
    
    # Write summary
    output.write("COST OPTIMIZATION REPORT\\n")
    output.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
    output.write(f"Total 30-day cost: ${cost_data['total_30_day_cost']:.2f}\\n")
    output.write(f"Daily average: ${cost_data['recent_avg_daily']:.2f}\\n")
    output.write(f"Trend: {cost_data['summary']['trend']} ({cost_data['trend_percentage']:.1f}%)\\n\\n")
    
    # Service costs
    output.write("SERVICE COSTS\\n")
    output.write("Service,Cost (USD)\\n")
    for service, cost in sorted(cost_data['services'].items(), key=lambda x: x[1], reverse=True):
        output.write(f"{service},{cost:.2f}\\n")
    
    output.write("\\n")
    
    # Recommendations
    output.write("OPTIMIZATION RECOMMENDATIONS\\n")
    output.write("Service,Current Cost,Recommendation,Potential Savings,Priority,Implementation\\n")
    for rec in recommendations:
        output.write(f"{rec['service']},{rec['current_cost']:.2f},{rec['recommendation']},{rec['potential_savings']:.2f},{rec['priority']},{rec['implementation']}\\n")
    
    return output.getvalue()

def send_cost_summary_email(sns_client, cost_data, recommendations, report_key):
    """Send cost summary email"""
    total_savings = sum(rec['potential_savings'] for rec in recommendations)
    
    message = f"""
📊 Monthly Cost Optimization Report - {os.environ['PROJECT_NAME']}

💰 Cost Summary:
• Total 30-day cost: ${cost_data['total_30_day_cost']:.2f}
• Daily average: ${cost_data['recent_avg_daily']:.2f}
• Trend: {cost_data['summary']['trend']} ({cost_data['trend_percentage']:.1f}%)
• Budget status: {(cost_data['total_30_day_cost'] / float(os.environ['MONTHLY_BUDGET']) * 100):.1f}% of monthly budget

💡 Optimization Opportunities:
• {len(recommendations)} recommendations identified
• Potential monthly savings: ${total_savings:.2f}
• Top recommendation: {recommendations[0]['recommendation'] if recommendations else 'None'}

📈 Top Services by Cost:
{chr(10).join([f"• {service}: ${cost:.2f}" for service, cost in sorted(cost_data['services'].items(), key=lambda x: x[1], reverse=True)[:3]])}

📋 Full Report: s3://{os.environ['S3_BUCKET']}/{report_key}
📊 Dashboard: {os.environ['DASHBOARD_URL']}

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
    """
    
    sns_client.publish(
        TopicArn=os.environ['SNS_TOPIC_ARN'],
        Subject=f"Monthly Cost Report: {os.environ['PROJECT_NAME']} - ${cost_data['total_30_day_cost']:.2f}",
        Message=message
    )
EOF
    filename = "cost_report.py"
  }
}

# Schedule for monthly cost reports
resource "aws_cloudwatch_event_rule" "monthly_cost_report" {
  name                = "${var.project_name}-monthly-cost-report-${var.environment}"
  description         = "Generate monthly cost optimization report"
  schedule_expression = "cron(0 9 1 * ? *)"  # First day of month at 9 AM UTC

  tags = merge(local.cost_tags, {
    Name = "${var.project_name}-monthly-cost-report-${var.environment}"
  })
}

resource "aws_cloudwatch_event_target" "cost_report_target" {
  rule      = aws_cloudwatch_event_rule.monthly_cost_report.name
  target_id = "CostReportTarget"
  arn       = aws_lambda_function.cost_report_generator.arn
}

resource "aws_lambda_permission" "allow_eventbridge_cost_report" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cost_report_generator.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.monthly_cost_report.arn
}

# CloudWatch Log Group for Cost Report Generator
resource "aws_cloudwatch_log_group" "cost_report_generator" {
  name              = "/aws/lambda/${var.project_name}-cost-report-generator-${var.environment}"
  retention_in_days = var.cloudwatch_log_retention_days
  kms_key_id        = aws_kms_key.cloudwatch.arn

  tags = merge(local.cost_tags, {
    Name = "${var.project_name}-cost-report-generator-logs-${var.environment}"
    Purpose = "Logs for cost report generator"
  })
}

# ===== COST OPTIMIZATION INSIGHTS =====

resource "aws_cloudwatch_insight_rule" "high_cost_lambda_functions" {
  name    = "${var.project_name}-high-cost-lambda-${var.environment}"
  pattern = jsonencode({
    source      = [{ "Namespace": "AWS/Lambda" }]
    logFormat   = "CWL"
    logGroups   = ["/aws/lambda/${var.project_name}-*"]
    fields      = ["@timestamp", "@message"]
    filter      = "@message like /ERROR/ or @message like /TIMEOUT/"
    stats       = "count() by bin(5m)"
    sort        = "@timestamp desc"
    limit       = 20
  })

  tags = merge(local.cost_tags, {
    Name = "${var.project_name}-high-cost-lambda-${var.environment}"
    Purpose = "Identify high-cost Lambda function patterns"
  })
}

# ===== OUTPUTS =====

output "cost_monitoring_dashboard_url" {
  description = "URL to cost optimization dashboard"
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.cost_optimization.dashboard_name}"
}

output "cost_optimization_functions" {
  description = "Cost optimization Lambda functions"
  value = {
    cost_optimizer     = aws_lambda_function.cost_optimizer.function_name
    cost_report_generator = aws_lambda_function.cost_report_generator.function_name
    business_hours_scaler = var.enable_business_hours_scaling ? aws_lambda_function.business_hours_scaler[0].function_name : null
  }
}
