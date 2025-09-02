# Lambda Functions

data "aws_caller_identity" "current" {}

# Universal Message Handler Lambda Function
resource "aws_lambda_function" "universal_message_handler" {
  filename         = "${path.module}/../deployment/lambda_package.zip"
  function_name    = "${var.project_name}-universal-message-handler-${var.environment}"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "handlers.universal_message_handler.lambda_handler"
  runtime         = var.lambda_runtime
  timeout         = var.lambda_timeout

  environment {
    variables = {
      ENVIRONMENT                = var.environment
      DYNAMODB_USER_TABLE       = aws_dynamodb_table.user_data.name
      DYNAMODB_SUBSCRIPTION_TABLE = aws_dynamodb_table.subscriptions.name
      DYNAMODB_USAGE_TABLE      = aws_dynamodb_table.usage.name
      DYNAMODB_PROMPT_CACHE_TABLE = aws_dynamodb_table.prompt_cache.name
      DYNAMODB_USER_LINKS_TABLE = var.enable_family_sharing ? aws_dynamodb_table.user_links[0].name : ""
      DYNAMODB_CONSENT_AUDIT_TABLE = var.gdpr_compliance_enabled ? aws_dynamodb_table.consent_audit[0].name : ""
      BEDROCK_MODEL_ID          = var.bedrock_models[0]  # Primary model
      ENABLE_FAMILY_SHARING     = var.enable_family_sharing
      GDPR_COMPLIANCE_ENABLED   = var.gdpr_compliance_enabled
      PRIVACY_MODE              = var.privacy_mode
      LOG_LEVEL                 = var.log_level
      ENABLE_COST_OPTIMIZATION  = var.enable_cost_optimization
      PROMPT_CACHE_TTL          = var.prompt_cache_ttl
      TWILIO_WEBHOOK_VALIDATION = var.enable_webhook_validation
    }
  }

  dynamic "vpc_config" {
    for_each = var.enable_vpc ? [1] : []
    content {
      subnet_ids         = var.vpc_subnet_ids
      security_group_ids = [aws_security_group.lambda[0].id]
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
      Name     = "${var.project_name}-universal-message-handler-${var.environment}"
      Function = "Universal message processing and AI nutrition assistance"
    },
    var.additional_tags
  )

  depends_on = [
    aws_iam_role_policy.lambda_execution,
    aws_cloudwatch_log_group.lambda_universal_message_handler
  ]
}

# Billing Webhook Lambda Function
resource "aws_lambda_function" "billing_handler" {
  filename         = "${path.module}/../deployment/lambda_package.zip"
  function_name    = "${var.project_name}-billing-handler-${var.environment}"
  role            = aws_iam_role.billing_lambda_execution.arn
  handler         = "handlers.billing_handler.lambda_handler"
  runtime         = var.lambda_runtime
  timeout         = 30  # Billing webhooks should be fast

  environment {
    variables = {
      ENVIRONMENT                = var.environment
      DYNAMODB_SUBSCRIPTION_TABLE = aws_dynamodb_table.subscriptions.name
      STRIPE_WEBHOOK_SECRET_PARAM = "${var.project_name}/stripe/webhook_secret"
      LOG_LEVEL                  = var.log_level
    }
  }

  kms_key_arn = aws_kms_key.lambda.arn

  tags = merge(
    {
      Name     = "${var.project_name}-billing-handler-${var.environment}"
      Function = "Stripe billing webhook processing"
    },
    var.additional_tags
  )

  depends_on = [
    aws_iam_role_policy.billing_lambda_execution,
    aws_cloudwatch_log_group.lambda_billing_handler
  ]
}

# Scheduler Lambda Function
resource "aws_lambda_function" "scheduler_handler" {
  filename         = "${path.module}/../deployment/lambda_package.zip"
  function_name    = "${var.project_name}-scheduler-handler-${var.environment}"
  role            = aws_iam_role.scheduler_lambda_execution.arn
  handler         = "handlers.scheduler_handler.lambda_handler"
  runtime         = var.lambda_runtime
  timeout         = var.lambda_timeout

  environment {
    variables = {
      ENVIRONMENT                = var.environment
      DYNAMODB_USER_TABLE       = aws_dynamodb_table.user_data.name
      DYNAMODB_PROMPT_CACHE_TABLE = aws_dynamodb_table.prompt_cache.name
      BEDROCK_MODEL_ID          = var.bedrock_models[0]
      LOG_LEVEL                 = var.log_level
      ENABLE_COST_OPTIMIZATION  = var.enable_cost_optimization
      PROMPT_CACHE_TTL          = var.prompt_cache_ttl
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
      Name     = "${var.project_name}-scheduler-handler-${var.environment}"
      Function = "Scheduled meal plan generation and user reminders"
    },
    var.additional_tags
  )

  depends_on = [
    aws_iam_role_policy.scheduler_lambda_execution,
    aws_cloudwatch_log_group.lambda_scheduler_handler
  ]
}

# CloudWatch Log Groups for Lambda Functions
resource "aws_cloudwatch_log_group" "lambda_universal_message_handler" {
  name              = "/aws/lambda/${var.project_name}-universal-message-handler-${var.environment}"
  retention_in_days = var.cloudwatch_log_retention_days
  kms_key_id        = aws_kms_key.cloudwatch.arn

  tags = merge(
    {
      Name     = "${var.project_name}-universal-message-handler-logs-${var.environment}"
      Function = "Universal message handler logs"
    },
    var.additional_tags
  )
}

resource "aws_cloudwatch_log_group" "lambda_billing_handler" {
  name              = "/aws/lambda/${var.project_name}-billing-handler-${var.environment}"
  retention_in_days = var.cloudwatch_log_retention_days
  kms_key_id        = aws_kms_key.cloudwatch.arn

  tags = merge(
    {
      Name     = "${var.project_name}-billing-handler-logs-${var.environment}"
      Function = "Billing handler logs"
    },
    var.additional_tags
  )
}

resource "aws_cloudwatch_log_group" "lambda_scheduler_handler" {
  name              = "/aws/lambda/${var.project_name}-scheduler-handler-${var.environment}"
  retention_in_days = var.cloudwatch_log_retention_days
  kms_key_id        = aws_kms_key.cloudwatch.arn

  tags = merge(
    {
      Name     = "${var.project_name}-scheduler-handler-logs-${var.environment}"
      Function = "Scheduler handler logs"
    },
    var.additional_tags
  )
}

# Lambda Permission for API Gateway to invoke Universal Message Handler
resource "aws_lambda_permission" "api_gateway_universal_message" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.universal_message_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# Lambda Permission for API Gateway to invoke Billing Handler
resource "aws_lambda_permission" "api_gateway_billing" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.billing_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# EventBridge Rule for Scheduler (Daily meal planning)
resource "aws_cloudwatch_event_rule" "daily_meal_planning" {
  name                = "${var.project_name}-daily-meal-planning-${var.environment}"
  description         = "Trigger daily meal planning for premium users"
  schedule_expression = var.daily_meal_planning_schedule

  tags = merge(
    {
      Name = "${var.project_name}-daily-meal-planning-${var.environment}"
    },
    var.additional_tags
  )
}

# EventBridge Target for Scheduler
resource "aws_cloudwatch_event_target" "scheduler_lambda" {
  rule      = aws_cloudwatch_event_rule.daily_meal_planning.name
  target_id = "SchedulerLambdaTarget"
  arn       = aws_lambda_function.scheduler_handler.arn
}

# Lambda Permission for EventBridge to invoke Scheduler
resource "aws_lambda_permission" "eventbridge_scheduler" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scheduler_handler.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_meal_planning.arn
}

# Lambda Function URLs (optional for direct webhook access)
resource "aws_lambda_function_url" "universal_message_handler" {
  count = var.enable_lambda_function_urls ? 1 : 0
  
  function_name      = aws_lambda_function.universal_message_handler.function_name
  authorization_type = "NONE"

  cors {
    allow_credentials = false
    allow_origins     = ["*"]
    allow_methods     = ["POST"]
    allow_headers     = ["date", "keep-alive"]
    expose_headers    = ["date", "keep-alive"]
    max_age          = 86400
  }
}

# Security Group for Lambda (if VPC enabled)
resource "aws_security_group" "lambda" {
  count = var.enable_vpc ? 1 : 0
  
  name        = "${var.project_name}-lambda-${var.environment}"
  description = "Security group for Lambda functions"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    {
      Name = "${var.project_name}-lambda-${var.environment}"
    },
    var.additional_tags
  )
}
