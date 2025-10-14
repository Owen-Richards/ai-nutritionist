# Outputs for API Gateway Module

# REST API Outputs
output "rest_api_id" {
  description = "ID of the REST API"
  value       = var.api_type == "REST" ? aws_api_gateway_rest_api.main[0].id : null
}

output "rest_api_arn" {
  description = "ARN of the REST API"
  value       = var.api_type == "REST" ? aws_api_gateway_rest_api.main[0].arn : null
}

output "rest_api_execution_arn" {
  description = "Execution ARN of the REST API"
  value       = var.api_type == "REST" ? aws_api_gateway_rest_api.main[0].execution_arn : null
}

output "rest_api_root_resource_id" {
  description = "Root resource ID of the REST API"
  value       = var.api_type == "REST" ? aws_api_gateway_rest_api.main[0].root_resource_id : null
}

# HTTP API Outputs
output "http_api_id" {
  description = "ID of the HTTP API"
  value       = var.api_type == "HTTP" ? aws_apigatewayv2_api.main[0].id : null
}

output "http_api_arn" {
  description = "ARN of the HTTP API"
  value       = var.api_type == "HTTP" ? aws_apigatewayv2_api.main[0].arn : null
}

output "http_api_execution_arn" {
  description = "Execution ARN of the HTTP API"
  value       = var.api_type == "HTTP" ? aws_apigatewayv2_api.main[0].execution_arn : null
}

output "http_api_endpoint" {
  description = "API endpoint URL of the HTTP API"
  value       = var.api_type == "HTTP" ? aws_apigatewayv2_api.main[0].api_endpoint : null
}

# Stage Outputs
output "stage_arn" {
  description = "ARN of the API Gateway stage"
  value = var.api_type == "REST" ? (
    length(aws_api_gateway_stage.main) > 0 ? aws_api_gateway_stage.main[0].arn : null
  ) : (
    length(aws_apigatewayv2_stage.main) > 0 ? aws_apigatewayv2_stage.main[0].arn : null
  )
}

output "stage_name" {
  description = "Name of the API Gateway stage"
  value = var.api_type == "REST" ? (
    length(aws_api_gateway_stage.main) > 0 ? aws_api_gateway_stage.main[0].stage_name : null
  ) : (
    length(aws_apigatewayv2_stage.main) > 0 ? aws_apigatewayv2_stage.main[0].name : null
  )
}

output "stage_invoke_url" {
  description = "Invoke URL of the API Gateway stage"
  value = var.api_type == "REST" ? (
    length(aws_api_gateway_stage.main) > 0 ? aws_api_gateway_stage.main[0].invoke_url : null
  ) : (
    length(aws_apigatewayv2_stage.main) > 0 ? aws_apigatewayv2_stage.main[0].invoke_url : null
  )
}

# Deployment Outputs
output "deployment_id" {
  description = "ID of the API Gateway deployment"
  value       = var.api_type == "REST" && length(aws_api_gateway_deployment.main) > 0 ? aws_api_gateway_deployment.main[0].id : null
}

# Custom Domain Outputs
output "domain_name" {
  description = "Custom domain name"
  value       = var.domain_name
}

output "domain_name_target" {
  description = "Target domain name for DNS configuration"
  value = var.domain_name != null ? (
    var.api_type == "REST" ? (
      length(aws_api_gateway_domain_name.main) > 0 ? aws_api_gateway_domain_name.main[0].cloudfront_domain_name : null
    ) : (
      length(aws_apigatewayv2_domain_name.main) > 0 ? aws_apigatewayv2_domain_name.main[0].domain_name_configuration[0].target_domain_name : null
    )
  ) : null
}

output "domain_name_hosted_zone_id" {
  description = "Hosted zone ID for the custom domain"
  value = var.domain_name != null ? (
    var.api_type == "REST" ? (
      length(aws_api_gateway_domain_name.main) > 0 ? aws_api_gateway_domain_name.main[0].cloudfront_zone_id : null
    ) : (
      length(aws_apigatewayv2_domain_name.main) > 0 ? aws_apigatewayv2_domain_name.main[0].domain_name_configuration[0].hosted_zone_id : null
    )
  ) : null
}

# CloudWatch Log Group
output "log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.api_gateway.name
}

output "log_group_arn" {
  description = "ARN of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.api_gateway.arn
}

# CloudWatch Alarms
output "cloudwatch_alarm_ids" {
  description = "List of CloudWatch alarm IDs"
  value = var.create_cloudwatch_alarms ? [
    aws_cloudwatch_metric_alarm.api_gateway_errors[0].id,
    aws_cloudwatch_metric_alarm.api_gateway_latency[0].id
  ] : []
}

# API Configuration
output "api_name" {
  description = "Name of the API"
  value       = var.api_name
}

output "api_type" {
  description = "Type of the API (REST or HTTP)"
  value       = var.api_type
}

output "endpoint_type" {
  description = "Endpoint type of the API"
  value       = var.endpoint_type
}

# Security
output "waf_web_acl_arn" {
  description = "ARN of the associated WAF Web ACL"
  value       = var.waf_web_acl_arn
}

# IAM Role
output "cloudwatch_role_arn" {
  description = "ARN of the CloudWatch IAM role"
  value       = var.api_type == "REST" && var.enable_cloudwatch_logging && length(aws_iam_role.api_gateway_cloudwatch) > 0 ? aws_iam_role.api_gateway_cloudwatch[0].arn : null
}

# URL Endpoints
output "api_endpoint" {
  description = "Base URL of the API"
  value = var.api_type == "REST" ? (
    length(aws_api_gateway_rest_api.main) > 0 ? "https://${aws_api_gateway_rest_api.main[0].id}.execute-api.${data.aws_region.current.name}.amazonaws.com" : null
  ) : (
    length(aws_apigatewayv2_api.main) > 0 ? aws_apigatewayv2_api.main[0].api_endpoint : null
  )
}

output "stage_url" {
  description = "Full URL to the API stage"
  value = var.domain_name != null ? (
    var.base_path != null ? "https://${var.domain_name}/${var.base_path}" : "https://${var.domain_name}"
  ) : (
    var.api_type == "REST" ? (
      length(aws_api_gateway_stage.main) > 0 ? aws_api_gateway_stage.main[0].invoke_url : null
    ) : (
      length(aws_apigatewayv2_stage.main) > 0 ? aws_apigatewayv2_stage.main[0].invoke_url : null
    )
  )
}

# Throttling Configuration
output "throttle_settings" {
  description = "Throttling configuration"
  value = {
    rate_limit  = var.throttle_rate_limit
    burst_limit = var.throttle_burst_limit
  }
}

# Resource Tags
output "tags" {
  description = "A map of tags assigned to the resource"
  value = var.api_type == "REST" ? (
    length(aws_api_gateway_rest_api.main) > 0 ? aws_api_gateway_rest_api.main[0].tags_all : {}
  ) : (
    length(aws_apigatewayv2_api.main) > 0 ? aws_apigatewayv2_api.main[0].tags_all : {}
  )
}

# Data source for region
data "aws_region" "current" {}
