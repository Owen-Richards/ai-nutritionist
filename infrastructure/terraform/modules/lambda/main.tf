# Lambda Module for AI Nutritionist
# Provides serverless compute infrastructure

locals {
  common_tags = merge(var.tags, {
    Module = "lambda"
  })

  # Function name with optional prefix
  function_name = var.function_name_prefix != null ? "${var.function_name_prefix}-${var.function_name}" : var.function_name
  
  # Determine if we need to create a deployment package
  create_package = var.source_code_path != null && var.deployment_package_path == null
  
  # Package filename
  package_filename = local.create_package ? "${path.module}/deployment.zip" : var.deployment_package_path
}

# Archive source code if source_code_path is provided
data "archive_file" "lambda_package" {
  count = local.create_package ? 1 : 0

  type        = "zip"
  source_dir  = var.source_code_path
  output_path = local.package_filename
  excludes    = var.package_excludes
}

# KMS Key for Lambda environment variables encryption
resource "aws_kms_key" "lambda" {
  count = var.kms_key_arn == null && var.environment_variables != {} ? 1 : 0

  description             = "KMS key for Lambda function encryption - ${local.function_name}"
  deletion_window_in_days = var.kms_deletion_window
  enable_key_rotation     = true

  tags = merge(local.common_tags, {
    Name = "${local.function_name}-lambda-kms-key"
    Type = "kms-key"
  })
}

resource "aws_kms_alias" "lambda" {
  count = var.kms_key_arn == null && var.environment_variables != {} ? 1 : 0

  name          = "alias/${local.function_name}-lambda"
  target_key_id = aws_kms_key.lambda[0].key_id
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.function_name}"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name = "${local.function_name}-logs"
    Type = "cloudwatch-log-group"
  })
}

# IAM Role for Lambda Execution
resource "aws_iam_role" "lambda_execution" {
  name = "${local.function_name}-lambda-execution-role"

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

  tags = local.common_tags
}

# Basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# VPC execution policy (if VPC configuration is provided)
resource "aws_iam_role_policy_attachment" "lambda_vpc_execution" {
  count = var.vpc_config != null ? 1 : 0

  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Custom IAM policy for additional permissions
resource "aws_iam_role_policy" "lambda_custom" {
  count = length(var.policy_statements) > 0 ? 1 : 0

  name = "${local.function_name}-lambda-custom-policy"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = var.policy_statements
  })
}

# Security Group for Lambda (if VPC configuration is provided)
resource "aws_security_group" "lambda" {
  count = var.vpc_config != null && var.create_security_group ? 1 : 0

  name_prefix = "${local.function_name}-lambda-"
  vpc_id      = var.vpc_config.vpc_id

  description = "Security group for Lambda function ${local.function_name}"

  # Allow HTTPS outbound (for API calls)
  egress {
    description = "HTTPS outbound"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow HTTP outbound (if needed)
  dynamic "egress" {
    for_each = var.allow_http_outbound ? [1] : []
    content {
      description = "HTTP outbound"
      from_port   = 80
      to_port     = 80
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    }
  }

  # Custom egress rules
  dynamic "egress" {
    for_each = var.security_group_egress_rules
    content {
      description     = egress.value.description
      from_port       = egress.value.from_port
      to_port         = egress.value.to_port
      protocol        = egress.value.protocol
      cidr_blocks     = lookup(egress.value, "cidr_blocks", null)
      security_groups = lookup(egress.value, "security_groups", null)
    }
  }

  # Custom ingress rules
  dynamic "ingress" {
    for_each = var.security_group_ingress_rules
    content {
      description     = ingress.value.description
      from_port       = ingress.value.from_port
      to_port         = ingress.value.to_port
      protocol        = ingress.value.protocol
      cidr_blocks     = lookup(ingress.value, "cidr_blocks", null)
      security_groups = lookup(ingress.value, "security_groups", null)
    }
  }

  tags = merge(local.common_tags, {
    Name = "${local.function_name}-lambda-sg"
    Type = "security-group"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Lambda Function
resource "aws_lambda_function" "main" {
  function_name = local.function_name
  role         = aws_iam_role.lambda_execution.arn
  
  # Code Configuration
  filename         = local.package_filename
  source_code_hash = local.create_package ? data.archive_file.lambda_package[0].output_base64sha256 : var.source_code_hash
  handler          = var.handler
  runtime          = var.runtime
  
  # Performance Configuration
  memory_size = var.memory_size
  timeout     = var.timeout

  # Environment Variables
  dynamic "environment" {
    for_each = var.environment_variables != {} ? [1] : []
    content {
      variables = var.environment_variables
    }
  }

  # VPC Configuration
  dynamic "vpc_config" {
    for_each = var.vpc_config != null ? [1] : []
    content {
      subnet_ids         = var.vpc_config.subnet_ids
      security_group_ids = concat(
        var.create_security_group ? [aws_security_group.lambda[0].id] : [],
        var.vpc_config.security_group_ids
      )
    }
  }

  # Dead Letter Queue Configuration
  dynamic "dead_letter_config" {
    for_each = var.dead_letter_target_arn != null ? [1] : []
    content {
      target_arn = var.dead_letter_target_arn
    }
  }

  # File System Configuration
  dynamic "file_system_config" {
    for_each = var.file_system_config != null ? [1] : []
    content {
      arn              = var.file_system_config.arn
      local_mount_path = var.file_system_config.local_mount_path
    }
  }

  # Image Configuration (for container images)
  dynamic "image_config" {
    for_each = var.package_type == "Image" ? [1] : []
    content {
      command           = var.image_config.command
      entry_point       = var.image_config.entry_point
      working_directory = var.image_config.working_directory
    }
  }

  # Tracing Configuration
  tracing_config {
    mode = var.tracing_mode
  }

  # KMS Key for environment variables encryption
  kms_key_arn = var.environment_variables != {} ? (
    var.kms_key_arn != null ? var.kms_key_arn : aws_kms_key.lambda[0].arn
  ) : null

  # Reserved Concurrency
  reserved_concurrent_executions = var.reserved_concurrent_executions

  # Package Type
  package_type = var.package_type
  image_uri    = var.package_type == "Image" ? var.image_uri : null

  # Layers
  layers = var.layers

  tags = merge(local.common_tags, {
    Name = local.function_name
    Type = "lambda-function"
  })

  depends_on = [
    aws_cloudwatch_log_group.lambda,
    aws_iam_role_policy_attachment.lambda_basic_execution
  ]
}

# Lambda Function URL (optional)
resource "aws_lambda_function_url" "main" {
  count = var.create_function_url ? 1 : 0

  function_name      = aws_lambda_function.main.function_name
  authorization_type = var.function_url_auth_type

  dynamic "cors" {
    for_each = var.function_url_cors != null ? [1] : []
    content {
      allow_credentials = var.function_url_cors.allow_credentials
      allow_headers     = var.function_url_cors.allow_headers
      allow_methods     = var.function_url_cors.allow_methods
      allow_origins     = var.function_url_cors.allow_origins
      expose_headers    = var.function_url_cors.expose_headers
      max_age          = var.function_url_cors.max_age
    }
  }
}

# Lambda Alias
resource "aws_lambda_alias" "main" {
  count = var.create_alias ? 1 : 0

  name             = var.alias_name
  description      = var.alias_description
  function_name    = aws_lambda_function.main.function_name
  function_version = var.alias_function_version

  dynamic "routing_config" {
    for_each = var.alias_routing_config != null ? [1] : []
    content {
      additional_version_weights = var.alias_routing_config.additional_version_weights
    }
  }
}

# Lambda Permission for API Gateway
resource "aws_lambda_permission" "api_gateway" {
  count = var.api_gateway_execution_arn != null ? 1 : 0

  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.main.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
  qualifier     = var.create_alias ? aws_lambda_alias.main[0].name : null
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  count = var.create_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${local.function_name}-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = var.error_alarm_threshold
  alarm_description   = "This metric monitors lambda errors"
  alarm_actions       = var.alarm_actions

  dimensions = {
    FunctionName = aws_lambda_function.main.function_name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  count = var.create_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${local.function_name}-lambda-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = var.duration_alarm_threshold
  alarm_description   = "This metric monitors lambda duration"
  alarm_actions       = var.alarm_actions

  dimensions = {
    FunctionName = aws_lambda_function.main.function_name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  count = var.create_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${local.function_name}-lambda-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = var.throttle_alarm_threshold
  alarm_description   = "This metric monitors lambda throttles"
  alarm_actions       = var.alarm_actions

  dimensions = {
    FunctionName = aws_lambda_function.main.function_name
  }

  tags = local.common_tags
}
