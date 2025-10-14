# ===== DYNAMODB AUTO-SCALING FOR COST OPTIMIZATION =====

# Auto-scaling for user_data table
resource "aws_appautoscaling_target" "user_data_read" {
  count              = var.dynamodb_enable_auto_scaling ? 1 : 0
  max_capacity       = var.dynamodb_max_read_capacity
  min_capacity       = var.dynamodb_min_read_capacity
  resource_id        = "table/${aws_dynamodb_table.user_data.name}"
  scalable_dimension = "dynamodb:table:ReadCapacityUnits"
  service_namespace  = "dynamodb"

  tags = merge(local.cost_tags, {
    Name = "${var.project_name}-user-data-read-scaling-${var.environment}"
    Purpose = "Auto-scaling for cost optimization"
  })
}

resource "aws_appautoscaling_policy" "user_data_read" {
  count              = var.dynamodb_enable_auto_scaling ? 1 : 0
  name               = "${var.project_name}-user-data-read-scaling-policy-${var.environment}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.user_data_read[0].resource_id
  scalable_dimension = aws_appautoscaling_target.user_data_read[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.user_data_read[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBReadCapacityUtilization"
    }
    target_value = var.dynamodb_target_utilization
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

resource "aws_appautoscaling_target" "user_data_write" {
  count              = var.dynamodb_enable_auto_scaling ? 1 : 0
  max_capacity       = var.dynamodb_max_write_capacity
  min_capacity       = var.dynamodb_min_write_capacity
  resource_id        = "table/${aws_dynamodb_table.user_data.name}"
  scalable_dimension = "dynamodb:table:WriteCapacityUnits"
  service_namespace  = "dynamodb"

  tags = merge(local.cost_tags, {
    Name = "${var.project_name}-user-data-write-scaling-${var.environment}"
    Purpose = "Auto-scaling for cost optimization"
  })
}

resource "aws_appautoscaling_policy" "user_data_write" {
  count              = var.dynamodb_enable_auto_scaling ? 1 : 0
  name               = "${var.project_name}-user-data-write-scaling-policy-${var.environment}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.user_data_write[0].resource_id
  scalable_dimension = aws_appautoscaling_target.user_data_write[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.user_data_write[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBWriteCapacityUtilization"
    }
    target_value = var.dynamodb_target_utilization
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# Auto-scaling for subscriptions table
resource "aws_appautoscaling_target" "subscriptions_read" {
  count              = var.dynamodb_enable_auto_scaling ? 1 : 0
  max_capacity       = var.dynamodb_max_read_capacity
  min_capacity       = var.dynamodb_min_read_capacity
  resource_id        = "table/${aws_dynamodb_table.subscriptions.name}"
  scalable_dimension = "dynamodb:table:ReadCapacityUnits"
  service_namespace  = "dynamodb"

  tags = merge(local.cost_tags, {
    Name = "${var.project_name}-subscriptions-read-scaling-${var.environment}"
    Purpose = "Auto-scaling for cost optimization"
  })
}

resource "aws_appautoscaling_policy" "subscriptions_read" {
  count              = var.dynamodb_enable_auto_scaling ? 1 : 0
  name               = "${var.project_name}-subscriptions-read-scaling-policy-${var.environment}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.subscriptions_read[0].resource_id
  scalable_dimension = aws_appautoscaling_target.subscriptions_read[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.subscriptions_read[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBReadCapacityUtilization"
    }
    target_value = var.dynamodb_target_utilization
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

resource "aws_appautoscaling_target" "subscriptions_write" {
  count              = var.dynamodb_enable_auto_scaling ? 1 : 0
  max_capacity       = var.dynamodb_max_write_capacity
  min_capacity       = var.dynamodb_min_write_capacity
  resource_id        = "table/${aws_dynamodb_table.subscriptions.name}"
  scalable_dimension = "dynamodb:table:WriteCapacityUnits"
  service_namespace  = "dynamodb"

  tags = merge(local.cost_tags, {
    Name = "${var.project_name}-subscriptions-write-scaling-${var.environment}"
    Purpose = "Auto-scaling for cost optimization"
  })
}

resource "aws_appautoscaling_policy" "subscriptions_write" {
  count              = var.dynamodb_enable_auto_scaling ? 1 : 0
  name               = "${var.project_name}-subscriptions-write-scaling-policy-${var.environment}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.subscriptions_write[0].resource_id
  scalable_dimension = aws_appautoscaling_target.subscriptions_write[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.subscriptions_write[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBWriteCapacityUtilization"
    }
    target_value = var.dynamodb_target_utilization
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# Auto-scaling for usage table
resource "aws_appautoscaling_target" "usage_read" {
  count              = var.dynamodb_enable_auto_scaling ? 1 : 0
  max_capacity       = var.dynamodb_max_read_capacity
  min_capacity       = var.dynamodb_min_read_capacity
  resource_id        = "table/${aws_dynamodb_table.usage.name}"
  scalable_dimension = "dynamodb:table:ReadCapacityUnits"
  service_namespace  = "dynamodb"

  tags = merge(local.cost_tags, {
    Name = "${var.project_name}-usage-read-scaling-${var.environment}"
    Purpose = "Auto-scaling for cost optimization"
  })
}

resource "aws_appautoscaling_policy" "usage_read" {
  count              = var.dynamodb_enable_auto_scaling ? 1 : 0
  name               = "${var.project_name}-usage-read-scaling-policy-${var.environment}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.usage_read[0].resource_id
  scalable_dimension = aws_appautoscaling_target.usage_read[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.usage_read[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBReadCapacityUtilization"
    }
    target_value = var.dynamodb_target_utilization
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

resource "aws_appautoscaling_target" "usage_write" {
  count              = var.dynamodb_enable_auto_scaling ? 1 : 0
  max_capacity       = var.dynamodb_max_write_capacity
  min_capacity       = var.dynamodb_min_write_capacity
  resource_id        = "table/${aws_dynamodb_table.usage.name}"
  scalable_dimension = "dynamodb:table:WriteCapacityUnits"
  service_namespace  = "dynamodb"

  tags = merge(local.cost_tags, {
    Name = "${var.project_name}-usage-write-scaling-${var.environment}"
    Purpose = "Auto-scaling for cost optimization"
  })
}

resource "aws_appautoscaling_policy" "usage_write" {
  count              = var.dynamodb_enable_auto_scaling ? 1 : 0
  name               = "${var.project_name}-usage-write-scaling-policy-${var.environment}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.usage_write[0].resource_id
  scalable_dimension = aws_appautoscaling_target.usage_write[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.usage_write[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBWriteCapacityUtilization"
    }
    target_value = var.dynamodb_target_utilization
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# Auto-scaling for prompt_cache table
resource "aws_appautoscaling_target" "prompt_cache_read" {
  count              = var.dynamodb_enable_auto_scaling ? 1 : 0
  max_capacity       = var.dynamodb_max_read_capacity
  min_capacity       = var.dynamodb_min_read_capacity
  resource_id        = "table/${aws_dynamodb_table.prompt_cache.name}"
  scalable_dimension = "dynamodb:table:ReadCapacityUnits"
  service_namespace  = "dynamodb"

  tags = merge(local.cost_tags, {
    Name = "${var.project_name}-prompt-cache-read-scaling-${var.environment}"
    Purpose = "Auto-scaling for cost optimization"
  })
}

resource "aws_appautoscaling_policy" "prompt_cache_read" {
  count              = var.dynamodb_enable_auto_scaling ? 1 : 0
  name               = "${var.project_name}-prompt-cache-read-scaling-policy-${var.environment}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.prompt_cache_read[0].resource_id
  scalable_dimension = aws_appautoscaling_target.prompt_cache_read[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.prompt_cache_read[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBReadCapacityUtilization"
    }
    target_value = var.dynamodb_target_utilization
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

resource "aws_appautoscaling_target" "prompt_cache_write" {
  count              = var.dynamodb_enable_auto_scaling ? 1 : 0
  max_capacity       = var.dynamodb_max_write_capacity
  min_capacity       = var.dynamodb_min_write_capacity
  resource_id        = "table/${aws_dynamodb_table.prompt_cache.name}"
  scalable_dimension = "dynamodb:table:WriteCapacityUnits"
  service_namespace  = "dynamodb"

  tags = merge(local.cost_tags, {
    Name = "${var.project_name}-prompt-cache-write-scaling-${var.environment}"
    Purpose = "Auto-scaling for cost optimization"
  })
}

resource "aws_appautoscaling_policy" "prompt_cache_write" {
  count              = var.dynamodb_enable_auto_scaling ? 1 : 0
  name               = "${var.project_name}-prompt-cache-write-scaling-policy-${var.environment}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.prompt_cache_write[0].resource_id
  scalable_dimension = aws_appautoscaling_target.prompt_cache_write[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.prompt_cache_write[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBWriteCapacityUtilization"
    }
    target_value = var.dynamodb_target_utilization
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# ===== S3 LIFECYCLE POLICIES FOR COST OPTIMIZATION =====

resource "aws_s3_bucket_lifecycle_configuration" "web_frontend_lifecycle" {
  bucket = aws_s3_bucket.web_frontend.id

  rule {
    id     = "cost_optimization_lifecycle"
    status = "Enabled"

    # Transition to IA after configured days
    transition {
      days          = var.s3_storage_class_transition_days
      storage_class = "STANDARD_IA"
    }

    # Transition to Glacier after configured days
    transition {
      days          = var.s3_glacier_transition_days
      storage_class = "GLACIER"
    }

    # Transition to Deep Archive after configured days
    transition {
      days          = var.s3_deep_archive_transition_days
      storage_class = "DEEP_ARCHIVE"
    }

    # Delete incomplete multipart uploads after 7 days
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }

    # Delete old versions after 90 days
    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# ===== API GATEWAY CACHING FOR COST OPTIMIZATION =====

resource "aws_api_gateway_method_settings" "caching" {
  count       = var.api_gateway_caching_enabled ? 1 : 0
  rest_api_id = aws_api_gateway_rest_api.main.id
  stage_name  = aws_api_gateway_stage.main.stage_name
  method_path = "*/*"

  settings {
    caching_enabled      = true
    cache_ttl_in_seconds = var.api_gateway_cache_ttl
    cache_key_parameters = ["method.request.querystring.user_id"]
    
    # Enable cache compression
    cache_data_encrypted = true
    
    # Throttling for cost control
    throttling_rate_limit  = var.api_gateway_throttling_rate_limit
    throttling_burst_limit = var.api_gateway_throttling_burst_limit
  }
}

# ===== CLOUDWATCH ALARMS FOR AUTO-SCALING MONITORING =====

resource "aws_cloudwatch_metric_alarm" "dynamodb_read_throttle" {
  count               = var.dynamodb_enable_auto_scaling ? 4 : 0
  alarm_name          = "${var.project_name}-dynamodb-read-throttle-${element(["user-data", "subscriptions", "usage", "prompt-cache"], count.index)}-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ReadThrottledEvents"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "DynamoDB read throttling detected - may need capacity adjustment"
  alarm_actions       = [aws_sns_topic.cost_alerts.arn]

  dimensions = {
    TableName = element([
      aws_dynamodb_table.user_data.name,
      aws_dynamodb_table.subscriptions.name,
      aws_dynamodb_table.usage.name,
      aws_dynamodb_table.prompt_cache.name
    ], count.index)
  }

  tags = merge(local.cost_tags, {
    Name = "${var.project_name}-dynamodb-read-throttle-${element(["user-data", "subscriptions", "usage", "prompt-cache"], count.index)}-${var.environment}"
  })
}

resource "aws_cloudwatch_metric_alarm" "dynamodb_write_throttle" {
  count               = var.dynamodb_enable_auto_scaling ? 4 : 0
  alarm_name          = "${var.project_name}-dynamodb-write-throttle-${element(["user-data", "subscriptions", "usage", "prompt-cache"], count.index)}-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "WriteThrottledEvents"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "DynamoDB write throttling detected - may need capacity adjustment"
  alarm_actions       = [aws_sns_topic.cost_alerts.arn]

  dimensions = {
    TableName = element([
      aws_dynamodb_table.user_data.name,
      aws_dynamodb_table.subscriptions.name,
      aws_dynamodb_table.usage.name,
      aws_dynamodb_table.prompt_cache.name
    ], count.index)
  }

  tags = merge(local.cost_tags, {
    Name = "${var.project_name}-dynamodb-write-throttle-${element(["user-data", "subscriptions", "usage", "prompt-cache"], count.index)}-${var.environment}"
  })
}

# ===== LAMBDA CONCURRENCY MANAGEMENT FOR COST CONTROL =====

resource "aws_lambda_function_event_invoke_config" "universal_message_handler_async" {
  function_name                = aws_lambda_function.universal_message_handler.function_name
  maximum_retry_attempts       = 2
  maximum_event_age_in_seconds = 21600  # 6 hours

  destination_config {
    on_failure {
      destination = aws_sqs_queue.dlq[0].arn
    }
  }
}

# ===== BUSINESS HOURS SCALING (OPTIONAL) =====

resource "aws_lambda_function" "business_hours_scaler" {
  count            = var.enable_business_hours_scaling ? 1 : 0
  filename         = data.archive_file.business_hours_scaler_zip[0].output_path
  source_code_hash = data.archive_file.business_hours_scaler_zip[0].output_base64sha256
  function_name    = "${var.project_name}-business-hours-scaler-${var.environment}"
  role            = aws_iam_role.cost_optimizer_role.arn
  handler         = "business_hours_scaler.lambda_handler"
  runtime         = "python3.11"
  timeout         = 300
  memory_size     = 256
  architectures   = ["arm64"]

  environment {
    variables = {
      ENVIRONMENT     = var.environment
      PROJECT_NAME    = var.project_name
      BUSINESS_START  = var.business_hours_start
      BUSINESS_END    = var.business_hours_end
      BUSINESS_DAYS   = join(",", var.business_days)
    }
  }

  tags = merge(local.cost_tags, {
    Name = "${var.project_name}-business-hours-scaler-${var.environment}"
    Purpose = "Business hours-based resource scaling"
  })
}

data "archive_file" "business_hours_scaler_zip" {
  count       = var.enable_business_hours_scaling ? 1 : 0
  type        = "zip"
  output_path = "${path.module}/temp/business_hours_scaler.zip"
  
  source {
    content = <<-EOF
import json
import boto3
import os
from datetime import datetime

def lambda_handler(event, context):
    """Scale resources based on business hours"""
    try:
        current_time = datetime.utcnow()
        current_hour = current_time.hour
        current_day = current_time.strftime("%a").upper()
        
        business_start = int(os.environ['BUSINESS_START'].split(':')[0])
        business_end = int(os.environ['BUSINESS_END'].split(':')[0])
        business_days = os.environ['BUSINESS_DAYS'].split(',')
        
        is_business_hours = (
            current_day in business_days and
            business_start <= current_hour < business_end
        )
        
        # Scale DynamoDB based on business hours
        scaling_client = boto3.client('application-autoscaling')
        
        if is_business_hours:
            # Scale up for business hours
            target_utilization = 80
            print("Scaling up for business hours")
        else:
            # Scale down for off-hours
            target_utilization = 50
            print("Scaling down for off-hours")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'is_business_hours': is_business_hours,
                'target_utilization': target_utilization,
                'current_time': current_time.isoformat()
            })
        }
        
    except Exception as e:
        print(f"Error in business hours scaler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
EOF
    filename = "business_hours_scaler.py"
  }
}

# Schedule for business hours scaling
resource "aws_cloudwatch_event_rule" "business_hours_scaling" {
  count               = var.enable_business_hours_scaling ? 1 : 0
  name                = "${var.project_name}-business-hours-scaling-${var.environment}"
  description         = "Trigger business hours scaling"
  schedule_expression = "cron(0 * * * ? *)"  # Run every hour

  tags = merge(local.cost_tags, {
    Name = "${var.project_name}-business-hours-scaling-${var.environment}"
  })
}

resource "aws_cloudwatch_event_target" "business_hours_scaler_target" {
  count     = var.enable_business_hours_scaling ? 1 : 0
  rule      = aws_cloudwatch_event_rule.business_hours_scaling[0].name
  target_id = "BusinessHoursScalerTarget"
  arn       = aws_lambda_function.business_hours_scaler[0].arn
}

resource "aws_lambda_permission" "allow_eventbridge_business_hours_scaler" {
  count         = var.enable_business_hours_scaling ? 1 : 0
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.business_hours_scaler[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.business_hours_scaling[0].arn
}
