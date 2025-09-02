# API Gateway Configuration

resource "aws_api_gateway_rest_api" "main" {
  name        = "${var.project_name}-api-${var.environment}"
  description = "AI Nutritionist API Gateway"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = merge(
    {
      Name = "${var.project_name}-api-${var.environment}"
    },
    var.additional_tags
  )
}

# API Gateway Account (for CloudWatch logging)
resource "aws_api_gateway_account" "main" {
  cloudwatch_role_arn = aws_iam_role.api_gateway_cloudwatch.arn
}

# API Gateway Deployment
resource "aws_api_gateway_deployment" "main" {
  depends_on = [
    aws_api_gateway_integration.webhook_post,
    aws_api_gateway_integration.billing_post,
    aws_api_gateway_integration.options_webhook,
    aws_api_gateway_integration.options_billing
  ]

  rest_api_id = aws_api_gateway_rest_api.main.id

  lifecycle {
    create_before_destroy = true
  }
}

# API Gateway Stage with logging and monitoring
resource "aws_api_gateway_stage" "main" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = var.environment

  xray_tracing_enabled = var.enable_xray_tracing
  
  dynamic "access_log_settings" {
    for_each = var.enable_api_gateway_logging ? [1] : []
    content {
      destination_arn = aws_cloudwatch_log_group.api_gateway[0].arn
      format = jsonencode({
        requestId      = "$requestId"
        requestTime    = "$requestTime"
        httpMethod     = "$httpMethod"
        resourcePath   = "$resourcePath"
        status         = "$status"
        responseLength = "$responseLength"
        responseTime   = "$responseTime"
        userAgent      = "$requestUserAgent"
        sourceIp       = "$sourceIp"
      })
    }
  }

  tags = merge(
    {
      Name = "${var.project_name}-api-stage-${var.environment}"
    },
    var.additional_tags
  )
}

# API Gateway Method Settings for detailed monitoring
resource "aws_api_gateway_method_settings" "main" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  stage_name  = aws_api_gateway_stage.main.stage_name
  method_path = "*/*"

  settings {
    metrics_enabled = var.enable_detailed_monitoring
    logging_level   = var.enable_api_gateway_logging ? "INFO" : "OFF"
    data_trace_enabled = var.enable_detailed_monitoring && var.environment != "prod"
  }
}

# CloudWatch Log Group for API Gateway (conditional)
resource "aws_cloudwatch_log_group" "api_gateway" {
  count = var.enable_api_gateway_logging ? 1 : 0
  
  name              = "API-Gateway-Execution-Logs_${aws_api_gateway_rest_api.main.id}/${var.environment}"
  retention_in_days = var.cloudwatch_log_retention_days
  kms_key_id        = aws_kms_key.cloudwatch.arn

  tags = merge(
    {
      Name = "${var.project_name}-api-gateway-logs-${var.environment}"
    },
    var.additional_tags
  )
}

# Webhook Resource (/webhook)
resource "aws_api_gateway_resource" "webhook" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "webhook"
}

# Webhook POST Method
resource "aws_api_gateway_method" "webhook_post" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.webhook.id
  http_method   = "POST"
  authorization = "NONE"

  request_parameters = {
    "method.request.header.X-Twilio-Signature" = false
  }
}

# Webhook POST Integration
resource "aws_api_gateway_integration" "webhook_post" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.webhook.id
  http_method             = aws_api_gateway_method.webhook_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.universal_message_handler.invoke_arn
}

# Webhook OPTIONS Method for CORS
resource "aws_api_gateway_method" "webhook_options" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.webhook.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# Webhook OPTIONS Integration
resource "aws_api_gateway_integration" "options_webhook" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.webhook.id
  http_method = aws_api_gateway_method.webhook_options.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

# Webhook OPTIONS Method Response
resource "aws_api_gateway_method_response" "webhook_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.webhook.id
  http_method = aws_api_gateway_method.webhook_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

# Webhook OPTIONS Integration Response
resource "aws_api_gateway_integration_response" "webhook_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.webhook.id
  http_method = aws_api_gateway_method.webhook_options.http_method
  status_code = aws_api_gateway_method_response.webhook_options.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Twilio-Signature'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# Billing Resource (/billing)
resource "aws_api_gateway_resource" "billing" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "billing"
}

# Billing POST Method
resource "aws_api_gateway_method" "billing_post" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.billing.id
  http_method   = "POST"
  authorization = "NONE"

  request_parameters = {
    "method.request.header.Stripe-Signature" = false
  }
}

# Billing POST Integration
resource "aws_api_gateway_integration" "billing_post" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.billing.id
  http_method             = aws_api_gateway_method.billing_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.billing_handler.invoke_arn
}

# Billing OPTIONS Method for CORS
resource "aws_api_gateway_method" "billing_options" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.billing.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# Billing OPTIONS Integration
resource "aws_api_gateway_integration" "options_billing" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.billing.id
  http_method = aws_api_gateway_method.billing_options.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

# Billing OPTIONS Method Response
resource "aws_api_gateway_method_response" "billing_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.billing.id
  http_method = aws_api_gateway_method.billing_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

# Billing OPTIONS Integration Response
resource "aws_api_gateway_integration_response" "billing_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.billing.id
  http_method = aws_api_gateway_method.billing_options.http_method
  status_code = aws_api_gateway_method_response.billing_options.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,Stripe-Signature'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# API Gateway Custom Domain (optional)
resource "aws_api_gateway_domain_name" "main" {
  count = var.custom_domain_name != "" ? 1 : 0
  
  domain_name     = var.custom_domain_name
  certificate_arn = var.ssl_certificate_arn

  tags = merge(
    {
      Name = "${var.project_name}-api-domain-${var.environment}"
    },
    var.additional_tags
  )
}

# API Gateway Base Path Mapping (for custom domain)
resource "aws_api_gateway_base_path_mapping" "main" {
  count = var.custom_domain_name != "" ? 1 : 0
  
  api_id      = aws_api_gateway_rest_api.main.id
  stage_name  = aws_api_gateway_stage.main.stage_name
  domain_name = aws_api_gateway_domain_name.main[0].domain_name
}

# WAF Web ACL for API Gateway (optional security)
resource "aws_wafv2_web_acl" "api_gateway" {
  count = var.enable_waf ? 1 : 0
  
  name  = "${var.project_name}-api-waf-${var.environment}"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  # Rate limiting rule
  rule {
    name     = "RateLimitRule"
    priority = 1

    override_action {
      none {}
    }

    statement {
      rate_based_statement {
        limit              = var.waf_rate_limit
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.project_name}-rate-limit-${var.environment}"
      sampled_requests_enabled   = true
    }

    action {
      block {}
    }
  }

  # AWS Managed Rules - Core Rule Set
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.project_name}-common-rules-${var.environment}"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.project_name}-waf-${var.environment}"
    sampled_requests_enabled   = true
  }

  tags = merge(
    {
      Name = "${var.project_name}-api-waf-${var.environment}"
    },
    var.additional_tags
  )
}

# Associate WAF with API Gateway
resource "aws_wafv2_web_acl_association" "api_gateway" {
  count = var.enable_waf ? 1 : 0
  
  resource_arn = aws_api_gateway_stage.main.arn
  web_acl_arn  = aws_wafv2_web_acl.api_gateway[0].arn
}
