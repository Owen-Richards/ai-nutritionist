# API Gateway Module for AI Nutritionist
# Provides REST and HTTP API Gateway infrastructure

locals {
  common_tags = merge(var.tags, {
    Module = "api-gateway"
  })

  # Determine API type configuration
  is_rest_api = var.api_type == "REST"
  is_http_api = var.api_type == "HTTP"
  
  # Generate default stage name if not provided
  default_stage_name = var.stage_name != null ? var.stage_name : var.environment
}

# CloudWatch Log Group for API Gateway
resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${var.api_name}"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name = "${var.api_name}-logs"
    Type = "cloudwatch-log-group"
  })
}

# REST API Gateway
resource "aws_api_gateway_rest_api" "main" {
  count = local.is_rest_api ? 1 : 0

  name        = var.api_name
  description = var.api_description

  endpoint_configuration {
    types = [var.endpoint_type]
    vpc_endpoint_ids = var.endpoint_type == "PRIVATE" ? var.vpc_endpoint_ids : null
  }

  policy = var.api_policy

  # Binary media types
  binary_media_types = var.binary_media_types

  tags = merge(local.common_tags, {
    Name = var.api_name
    Type = "rest-api"
  })
}

# HTTP API Gateway (API Gateway v2)
resource "aws_apigatewayv2_api" "main" {
  count = local.is_http_api ? 1 : 0

  name          = var.api_name
  description   = var.api_description
  protocol_type = "HTTP"

  # CORS configuration
  dynamic "cors_configuration" {
    for_each = var.cors_configuration != null ? [var.cors_configuration] : []
    content {
      allow_credentials = lookup(cors_configuration.value, "allow_credentials", false)
      allow_headers     = lookup(cors_configuration.value, "allow_headers", [])
      allow_methods     = lookup(cors_configuration.value, "allow_methods", [])
      allow_origins     = lookup(cors_configuration.value, "allow_origins", [])
      expose_headers    = lookup(cors_configuration.value, "expose_headers", [])
      max_age          = lookup(cors_configuration.value, "max_age", 0)
    }
  }

  tags = merge(local.common_tags, {
    Name = var.api_name
    Type = "http-api"
  })
}

# REST API Deployment
resource "aws_api_gateway_deployment" "main" {
  count = local.is_rest_api ? 1 : 0

  rest_api_id = aws_api_gateway_rest_api.main[0].id

  triggers = {
    redeployment = sha1(jsonencode([
      var.api_resources,
      var.api_methods
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_api_gateway_rest_api.main
  ]
}

# REST API Stage
resource "aws_api_gateway_stage" "main" {
  count = local.is_rest_api ? 1 : 0

  deployment_id = aws_api_gateway_deployment.main[0].id
  rest_api_id   = aws_api_gateway_rest_api.main[0].id
  stage_name    = local.default_stage_name

  # Logging configuration
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip            = "$context.identity.sourceIp"
      caller        = "$context.identity.caller"
      user          = "$context.identity.user"
      requestTime   = "$context.requestTime"
      httpMethod    = "$context.httpMethod"
      resourcePath  = "$context.resourcePath"
      status        = "$context.status"
      protocol      = "$context.protocol"
      responseLength = "$context.responseLength"
      errorMessage  = "$context.error.message"
      errorType     = "$context.error.messageString"
    })
  }

  # X-Ray tracing
  xray_tracing_enabled = var.xray_tracing_enabled

  # Throttling
  dynamic "throttle_settings" {
    for_each = var.throttle_rate_limit > 0 ? [1] : []
    content {
      rate_limit  = var.throttle_rate_limit
      burst_limit = var.throttle_burst_limit
    }
  }

  tags = merge(local.common_tags, {
    Name = "${var.api_name}-${local.default_stage_name}"
    Type = "api-stage"
  })
}

# HTTP API Stage
resource "aws_apigatewayv2_stage" "main" {
  count = local.is_http_api ? 1 : 0

  api_id    = aws_apigatewayv2_api.main[0].id
  name      = local.default_stage_name
  auto_deploy = var.auto_deploy

  # Logging configuration
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip            = "$context.identity.sourceIp"
      requestTime   = "$context.requestTime"
      httpMethod    = "$context.httpMethod"
      routeKey      = "$context.routeKey"
      status        = "$context.status"
      protocol      = "$context.protocol"
      responseLength = "$context.responseLength"
      errorMessage  = "$context.error.message"
    })
  }

  # Throttling
  dynamic "default_route_settings" {
    for_each = var.throttle_rate_limit > 0 ? [1] : []
    content {
      throttling_rate_limit  = var.throttle_rate_limit
      throttling_burst_limit = var.throttle_burst_limit
    }
  }

  tags = merge(local.common_tags, {
    Name = "${var.api_name}-${local.default_stage_name}"
    Type = "api-stage"
  })
}

# Custom Domain Name (optional)
resource "aws_api_gateway_domain_name" "main" {
  count = local.is_rest_api && var.domain_name != null ? 1 : 0

  domain_name              = var.domain_name
  certificate_arn          = var.certificate_arn
  security_policy          = var.security_policy

  endpoint_configuration {
    types = [var.domain_endpoint_type]
  }

  tags = merge(local.common_tags, {
    Name = var.domain_name
    Type = "api-domain"
  })
}

# HTTP API Custom Domain
resource "aws_apigatewayv2_domain_name" "main" {
  count = local.is_http_api && var.domain_name != null ? 1 : 0

  domain_name = var.domain_name

  domain_name_configuration {
    certificate_arn = var.certificate_arn
    endpoint_type   = var.domain_endpoint_type
    security_policy = var.security_policy
  }

  tags = merge(local.common_tags, {
    Name = var.domain_name
    Type = "api-domain"
  })
}

# Base Path Mapping (REST API)
resource "aws_api_gateway_base_path_mapping" "main" {
  count = local.is_rest_api && var.domain_name != null ? 1 : 0

  api_id      = aws_api_gateway_rest_api.main[0].id
  stage_name  = aws_api_gateway_stage.main[0].stage_name
  domain_name = aws_api_gateway_domain_name.main[0].domain_name
  base_path   = var.base_path
}

# API Mapping (HTTP API)
resource "aws_apigatewayv2_api_mapping" "main" {
  count = local.is_http_api && var.domain_name != null ? 1 : 0

  api_id      = aws_apigatewayv2_api.main[0].id
  domain_name = aws_apigatewayv2_domain_name.main[0].id
  stage       = aws_apigatewayv2_stage.main[0].id
  api_mapping_key = var.base_path
}

# API Gateway Account (for CloudWatch logging)
resource "aws_api_gateway_account" "main" {
  count = local.is_rest_api && var.enable_cloudwatch_logging ? 1 : 0

  cloudwatch_role_arn = aws_iam_role.api_gateway_cloudwatch[0].arn
}

# IAM Role for API Gateway CloudWatch logging
resource "aws_iam_role" "api_gateway_cloudwatch" {
  count = local.is_rest_api && var.enable_cloudwatch_logging ? 1 : 0

  name = "${var.api_name}-api-gateway-cloudwatch-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# IAM Policy for API Gateway CloudWatch logging
resource "aws_iam_role_policy_attachment" "api_gateway_cloudwatch" {
  count = local.is_rest_api && var.enable_cloudwatch_logging ? 1 : 0

  role       = aws_iam_role.api_gateway_cloudwatch[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}

# WAF Web ACL Association (optional)
resource "aws_wafv2_web_acl_association" "main" {
  count = var.waf_web_acl_arn != null && local.is_rest_api ? 1 : 0

  resource_arn = aws_api_gateway_stage.main[0].arn
  web_acl_arn  = var.waf_web_acl_arn
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "api_gateway_errors" {
  count = var.create_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.api_name}-api-gateway-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = local.is_rest_api ? "4XXError" : "4xx"
  namespace           = local.is_rest_api ? "AWS/ApiGateway" : "AWS/ApiGatewayV2"
  period              = "300"
  statistic           = "Sum"
  threshold           = var.error_alarm_threshold
  alarm_description   = "This metric monitors API Gateway 4xx errors"
  alarm_actions       = var.alarm_actions

  dimensions = local.is_rest_api ? {
    ApiName   = aws_api_gateway_rest_api.main[0].name
    Stage     = aws_api_gateway_stage.main[0].stage_name
  } : {
    ApiId = aws_apigatewayv2_api.main[0].id
    Stage = aws_apigatewayv2_stage.main[0].name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "api_gateway_latency" {
  count = var.create_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.api_name}-api-gateway-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = local.is_rest_api ? "Latency" : "IntegrationLatency"
  namespace           = local.is_rest_api ? "AWS/ApiGateway" : "AWS/ApiGatewayV2"
  period              = "300"
  statistic           = "Average"
  threshold           = var.latency_alarm_threshold
  alarm_description   = "This metric monitors API Gateway latency"
  alarm_actions       = var.alarm_actions

  dimensions = local.is_rest_api ? {
    ApiName   = aws_api_gateway_rest_api.main[0].name
    Stage     = aws_api_gateway_stage.main[0].stage_name
  } : {
    ApiId = aws_apigatewayv2_api.main[0].id
    Stage = aws_apigatewayv2_stage.main[0].name
  }

  tags = local.common_tags
}
