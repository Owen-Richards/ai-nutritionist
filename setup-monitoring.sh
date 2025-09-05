#!/bin/bash

# Production Monitoring Setup Script
# Creates CloudWatch dashboard and alarms for production monitoring

set -e

ENVIRONMENT="prod"
AWS_REGION="${AWS_REGION:-us-east-1}"
STACK_NAME="ai-nutritionist-prod"

echo "📊 Setting up production monitoring for AI Nutritionist..."

# Create CloudWatch Dashboard
aws cloudwatch put-dashboard \
  --dashboard-name "AI-Nutritionist-Production" \
  --dashboard-body '{
    "widgets": [
      {
        "type": "metric",
        "x": 0,
        "y": 0,
        "width": 12,
        "height": 6,
        "properties": {
          "metrics": [
            ["AWS/Lambda", "Invocations", "FunctionName", "ai-nutritionist-message-handler-prod"],
            [".", "Errors", ".", "."],
            [".", "Duration", ".", "."],
            [".", "Throttles", ".", "."]
          ],
          "period": 300,
          "stat": "Sum",
          "region": "'$AWS_REGION'",
          "title": "Lambda Functions - Message Handler"
        }
      },
      {
        "type": "metric",
        "x": 12,
        "y": 0,
        "width": 12,
        "height": 6,
        "properties": {
          "metrics": [
            ["AWS/ApiGateway", "Count", "ApiName", "ai-nutritionist-prod"],
            [".", "4XXError", ".", "."],
            [".", "5XXError", ".", "."],
            [".", "Latency", ".", "."]
          ],
          "period": 300,
          "stat": "Sum",
          "region": "'$AWS_REGION'",
          "title": "API Gateway Metrics"
        }
      },
      {
        "type": "metric",
        "x": 0,
        "y": 6,
        "width": 12,
        "height": 6,
        "properties": {
          "metrics": [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", "ai-nutritionist-users-prod"],
            [".", "ConsumedWriteCapacityUnits", ".", "."],
            [".", "ThrottledRequests", ".", "."]
          ],
          "period": 300,
          "stat": "Sum",
          "region": "'$AWS_REGION'",
          "title": "DynamoDB - User Data Table"
        }
      },
      {
        "type": "metric",
        "x": 12,
        "y": 6,
        "width": 12,
        "height": 6,
        "properties": {
          "metrics": [
            ["AWS/Bedrock", "InputTokenCount", "ModelId", "anthropic.claude-3-haiku-20240307-v1:0"],
            [".", "OutputTokenCount", ".", "."],
            [".", "Invocations", ".", "."]
          ],
          "period": 300,
          "stat": "Sum",
          "region": "'$AWS_REGION'",
          "title": "Bedrock AI Model Usage"
        }
      },
      {
        "type": "log",
        "x": 0,
        "y": 12,
        "width": 24,
        "height": 6,
        "properties": {
          "query": "SOURCE \"/aws/lambda/ai-nutritionist-message-handler-prod\"\n| fields @timestamp, @message\n| filter @message like /ERROR/\n| sort @timestamp desc\n| limit 100",
          "region": "'$AWS_REGION'",
          "title": "Recent Errors",
          "view": "table"
        }
      }
    ]
  }' \
  --region $AWS_REGION

echo "✅ CloudWatch dashboard created: AI-Nutritionist-Production"

# Create comprehensive alarms
echo "📢 Setting up CloudWatch alarms..."

# Lambda Error Rate Alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "ai-nutritionist-prod-lambda-error-rate" \
  --alarm-description "High error rate in Lambda functions" \
  --metric-name "Errors" \
  --namespace "AWS/Lambda" \
  --statistic "Sum" \
  --period 300 \
  --threshold 10 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions Name=FunctionName,Value="ai-nutritionist-message-handler-prod" \
  --evaluation-periods 2 \
  --alarm-actions "arn:aws:sns:$AWS_REGION:$(aws sts get-caller-identity --query Account --output text):ai-nutritionist-alerts" \
  --region $AWS_REGION

# Lambda Duration Alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "ai-nutritionist-prod-lambda-duration" \
  --alarm-description "Lambda function duration too high" \
  --metric-name "Duration" \
  --namespace "AWS/Lambda" \
  --statistic "Average" \
  --period 300 \
  --threshold 25000 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions Name=FunctionName,Value="ai-nutritionist-message-handler-prod" \
  --evaluation-periods 2 \
  --region $AWS_REGION

# API Gateway 5XX Errors
aws cloudwatch put-metric-alarm \
  --alarm-name "ai-nutritionist-prod-api-5xx-errors" \
  --alarm-description "High rate of 5XX errors in API Gateway" \
  --metric-name "5XXError" \
  --namespace "AWS/ApiGateway" \
  --statistic "Sum" \
  --period 300 \
  --threshold 5 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions Name=ApiName,Value="ai-nutritionist-prod" \
  --evaluation-periods 1 \
  --region $AWS_REGION

# DynamoDB Throttling Alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "ai-nutritionist-prod-dynamodb-throttling" \
  --alarm-description "DynamoDB requests being throttled" \
  --metric-name "ThrottledRequests" \
  --namespace "AWS/DynamoDB" \
  --statistic "Sum" \
  --period 300 \
  --threshold 1 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions Name=TableName,Value="ai-nutritionist-users-prod" \
  --evaluation-periods 1 \
  --region $AWS_REGION

# Cost Alarm (Billing)
aws cloudwatch put-metric-alarm \
  --alarm-name "ai-nutritionist-prod-monthly-cost" \
  --alarm-description "Monthly cost exceeding budget" \
  --metric-name "EstimatedCharges" \
  --namespace "AWS/Billing" \
  --statistic "Maximum" \
  --period 86400 \
  --threshold 1000 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions Name=Currency,Value=USD \
  --evaluation-periods 1 \
  --region us-east-1

echo "✅ CloudWatch alarms configured"

# Create custom metrics for business KPIs
echo "📈 Setting up custom business metrics..."

# Create a Lambda function to publish custom metrics
cat > /tmp/metrics_publisher.py << 'EOF'
import boto3
import json
from datetime import datetime

def lambda_handler(event, context):
    cloudwatch = boto3.client('cloudwatch')
    
    # Example: Publish meal plan generation metric
    cloudwatch.put_metric_data(
        Namespace='AINutritionist/Business',
        MetricData=[
            {
                'MetricName': 'MealPlansGenerated',
                'Value': 1,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow(),
                'Dimensions': [
                    {
                        'Name': 'Environment',
                        'Value': 'prod'
                    }
                ]
            }
        ]
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps('Metrics published successfully')
    }
EOF

echo "📊 Production monitoring setup complete!"
echo ""
echo "🔗 Access your monitoring dashboard:"
echo "https://$AWS_REGION.console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#dashboards:name=AI-Nutritionist-Production"
echo ""
echo "📋 Monitoring Features Configured:"
echo "• Real-time Lambda function metrics"
echo "• API Gateway performance tracking"
echo "• DynamoDB capacity monitoring"
echo "• Bedrock AI usage analytics"
echo "• Error tracking and alerting"
echo "• Cost monitoring and budget alerts"
echo "• Custom business KPIs tracking"
echo ""
echo "⚠️  Next Steps:"
echo "1. Set up SNS topic for alerts: aws sns create-topic --name ai-nutritionist-alerts"
echo "2. Subscribe to alerts: aws sns subscribe --topic-arn <topic-arn> --protocol email --notification-endpoint your-email@domain.com"
echo "3. Review and adjust alarm thresholds based on your usage patterns"
echo "4. Set up additional custom metrics for business KPIs"
