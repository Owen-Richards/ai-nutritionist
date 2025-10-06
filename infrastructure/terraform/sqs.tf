# SQS Dead Letter Queue for Lambda Error Handling
# Best Practice: Capture failed messages for debugging and reprocessing

# Dead Letter Queue for Lambda Functions
resource "aws_sqs_queue" "lambda_dlq" {
  name = "${var.project_name}-lambda-dlq-${var.environment}"

  # Message retention
  message_retention_seconds = var.dlq_message_retention_seconds
  
  # Visibility timeout
  visibility_timeout_seconds = var.lambda_timeout * 6
  
  # Server-side encryption
  kms_master_key_id                 = aws_kms_key.sqs.arn
  kms_data_key_reuse_period_seconds = 300

  tags = merge(
    {
      Name    = "${var.project_name}-lambda-dlq-${var.environment}"
      Purpose = "Dead letter queue for failed Lambda executions"
      Type    = "DLQ"
    },
    var.additional_tags
  )
}

# KMS Key for SQS Encryption
resource "aws_kms_key" "sqs" {
  description             = "KMS key for SQS encryption - ${var.project_name} ${var.environment}"
  deletion_window_in_days = var.environment == "prod" ? 30 : 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow SQS Service"
        Effect = "Allow"
        Principal = {
          Service = "sqs.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey",
          "kms:Encrypt",
          "kms:GenerateDataKey*",
          "kms:ReEncrypt*"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(
    {
      Name    = "${var.project_name}-sqs-key-${var.environment}"
      Purpose = "SQS encryption"
      Service = "SQS"
    },
    var.additional_tags
  )
}

resource "aws_kms_alias" "sqs" {
  name          = "alias/${var.project_name}-sqs-${var.environment}"
  target_key_id = aws_kms_key.sqs.key_id
}

# Queue for Processing Failed Messages
resource "aws_sqs_queue" "failed_message_processor" {
  name = "${var.project_name}-failed-messages-${var.environment}"

  # Message settings
  message_retention_seconds = var.failed_message_retention_seconds
  visibility_timeout_seconds = 300
  
  # Redrive policy to move messages back to DLQ after max receives
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.lambda_dlq.arn
    maxReceiveCount     = 3
  })

  # Server-side encryption
  kms_master_key_id                 = aws_kms_key.sqs.arn
  kms_data_key_reuse_period_seconds = 300

  tags = merge(
    {
      Name    = "${var.project_name}-failed-messages-${var.environment}"
      Purpose = "Process and retry failed messages"
      Type    = "Processing"
    },
    var.additional_tags
  )
}

# Queue for Async Message Processing
resource "aws_sqs_queue" "async_processing" {
  count = var.enable_async_processing ? 1 : 0
  
  name = "${var.project_name}-async-processing-${var.environment}"

  # Message settings for async processing
  message_retention_seconds  = var.async_message_retention_seconds
  visibility_timeout_seconds = var.lambda_timeout * 6
  delay_seconds             = 0
  max_message_size          = 262144
  receive_wait_time_seconds = 20  # Long polling

  # Redrive policy
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.lambda_dlq.arn
    maxReceiveCount     = 5
  })

  # Server-side encryption
  kms_master_key_id                 = aws_kms_key.sqs.arn
  kms_data_key_reuse_period_seconds = 300

  tags = merge(
    {
      Name    = "${var.project_name}-async-processing-${var.environment}"
      Purpose = "Asynchronous message processing"
      Type    = "Async"
    },
    var.additional_tags
  )
}

# Lambda Event Source Mapping for Failed Message Processor
resource "aws_lambda_event_source_mapping" "failed_message_processor" {
  count = var.enable_dlq_processing ? 1 : 0
  
  event_source_arn = aws_sqs_queue.failed_message_processor.arn
  function_name    = aws_lambda_function.failed_message_processor[0].arn
  batch_size       = 10
  
  # Error handling
  maximum_batching_window_in_seconds = 5
  
  scaling_config {
    maximum_concurrency = var.dlq_processor_max_concurrency
  }
}

# Lambda Function for Processing Failed Messages
resource "aws_lambda_function" "failed_message_processor" {
  count = var.enable_dlq_processing ? 1 : 0
  
  filename         = "${path.module}/../deployment/lambda_package.zip"
  function_name    = "${var.project_name}-failed-message-processor-${var.environment}"
  role            = aws_iam_role.dlq_processor[0].arn
  handler         = "handlers.failed_message_processor.lambda_handler"
  runtime         = var.lambda_runtime
  timeout         = 300  # 5 minutes for reprocessing
  memory_size     = 512  # More memory for processing complex failures
  
  # Performance Optimization
  architectures = [var.lambda_architecture]

  environment {
    variables = {
      ENVIRONMENT                = var.environment
      ORIGINAL_FUNCTION_NAME     = aws_lambda_function.universal_message_handler.function_name
      LOG_LEVEL                 = var.log_level
      MAX_RETRY_ATTEMPTS        = "3"
      FAILED_MESSAGE_QUEUE_URL  = aws_sqs_queue.failed_message_processor.url
    }
  }

  dynamic "vpc_config" {
    for_each = var.enable_vpc ? [1] : []
    content {
      subnet_ids         = aws_subnet.private[*].id
      security_group_ids = [aws_security_group.lambda_enhanced[0].id]
    }
  }

  kms_key_arn = aws_kms_key.lambda.arn

  dynamic "tracing_config" {
    for_each = var.enable_xray_tracing ? [1] : []
    content {
      mode = "Active"
    }
  }

  tags = merge(
    {
      Name        = "${var.project_name}-failed-message-processor-${var.environment}"
      Purpose     = "Process and retry failed messages"
      Component   = "ErrorHandler"
    },
    var.additional_tags
  )

  depends_on = [
    aws_iam_role_policy_attachment.dlq_processor_policy,
    aws_cloudwatch_log_group.lambda_failed_message_processor
  ]
}

# IAM Role for DLQ Processor Lambda
resource "aws_iam_role" "dlq_processor" {
  count = var.enable_dlq_processing ? 1 : 0
  
  name = "${var.project_name}-dlq-processor-role-${var.environment}"

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

  tags = merge(
    {
      Name    = "${var.project_name}-dlq-processor-role-${var.environment}"
      Purpose = "DLQ processor lambda execution role"
    },
    var.additional_tags
  )
}

# IAM Policy for DLQ Processor
resource "aws_iam_role_policy" "dlq_processor" {
  count = var.enable_dlq_processing ? 1 : 0
  
  name = "${var.project_name}-dlq-processor-policy-${var.environment}"
  role = aws_iam_role.dlq_processor[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # CloudWatch Logs
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.project_name}-failed-message-processor-*"
      },
      # SQS access
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:SendMessage"
        ]
        Resource = [
          aws_sqs_queue.lambda_dlq.arn,
          aws_sqs_queue.failed_message_processor.arn
        ]
      },
      # Lambda invoke permissions
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = aws_lambda_function.universal_message_handler.arn
      },
      # KMS permissions
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = [
          aws_kms_key.sqs.arn,
          aws_kms_key.lambda.arn
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "dlq_processor_policy" {
  count = var.enable_dlq_processing ? 1 : 0
  
  role       = aws_iam_role.dlq_processor[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# CloudWatch Log Group for DLQ Processor
resource "aws_cloudwatch_log_group" "lambda_failed_message_processor" {
  count = var.enable_dlq_processing ? 1 : 0
  
  name              = "/aws/lambda/${var.project_name}-failed-message-processor-${var.environment}"
  retention_in_days = var.cloudwatch_log_retention_days
  kms_key_id        = aws_kms_key.cloudwatch.arn

  tags = merge(
    {
      Name = "${var.project_name}-failed-message-processor-logs-${var.environment}"
    },
    var.additional_tags
  )
}

# CloudWatch Alarms for SQS Queues
resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  count = var.enable_monitoring ? 1 : 0
  
  alarm_name          = "${var.project_name}-dlq-messages-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ApproximateNumberOfMessages"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Average"
  threshold           = "10"
  alarm_description   = "This metric monitors DLQ message count"
  alarm_actions       = var.enable_sns_alerts ? [aws_sns_topic.alerts[0].arn] : []

  dimensions = {
    QueueName = aws_sqs_queue.lambda_dlq.name
  }

  tags = merge(
    {
      Name = "${var.project_name}-dlq-alarm-${var.environment}"
    },
    var.additional_tags
  )
}

resource "aws_cloudwatch_metric_alarm" "failed_processor_queue_age" {
  count = var.enable_monitoring && var.enable_dlq_processing ? 1 : 0
  
  alarm_name          = "${var.project_name}-failed-processor-queue-age-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ApproximateAgeOfOldestMessage"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Maximum"
  threshold           = "1800"  # 30 minutes
  alarm_description   = "This metric monitors the age of messages in failed processor queue"
  alarm_actions       = var.enable_sns_alerts ? [aws_sns_topic.alerts[0].arn] : []

  dimensions = {
    QueueName = aws_sqs_queue.failed_message_processor.name
  }

  tags = merge(
    {
      Name = "${var.project_name}-failed-processor-age-alarm-${var.environment}"
    },
    var.additional_tags
  )
}
