# Infrastructure Outputs

# API Gateway Outputs
output "api_gateway_url" {
  description = "API Gateway base URL"
  value       = aws_api_gateway_stage.main.invoke_url
}

output "api_gateway_id" {
  description = "API Gateway REST API ID"
  value       = aws_api_gateway_rest_api.main.id
}

output "webhook_url" {
  description = "Webhook endpoint URL for Twilio integration"
  value       = "${aws_api_gateway_stage.main.invoke_url}/webhook"
}

output "billing_webhook_url" {
  description = "Billing webhook endpoint URL for Stripe integration"
  value       = "${aws_api_gateway_stage.main.invoke_url}/billing"
}

# CloudFront Outputs
output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.web_frontend.id
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.web_frontend.domain_name
}

output "website_url" {
  description = "Website URL (CloudFront distribution)"
  value       = "https://${aws_cloudfront_distribution.web_frontend.domain_name}"
}

# S3 Outputs
output "s3_bucket_name" {
  description = "S3 bucket name for web frontend"
  value       = aws_s3_bucket.web_frontend.bucket
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN for web frontend"
  value       = aws_s3_bucket.web_frontend.arn
}

# Lambda Function Outputs
output "lambda_function_names" {
  description = "Lambda function names"
  value = {
    universal_message_handler = aws_lambda_function.universal_message_handler.function_name
    billing_handler          = aws_lambda_function.billing_handler.function_name
    scheduler_handler        = aws_lambda_function.scheduler_handler.function_name
  }
}

output "lambda_function_arns" {
  description = "Lambda function ARNs"
  value = {
    universal_message_handler = aws_lambda_function.universal_message_handler.arn
    billing_handler          = aws_lambda_function.billing_handler.arn
    scheduler_handler        = aws_lambda_function.scheduler_handler.arn
  }
}

# DynamoDB Outputs
output "dynamodb_table_names" {
  description = "DynamoDB table names"
  value = {
    user_data     = aws_dynamodb_table.user_data.name
    subscriptions = aws_dynamodb_table.subscriptions.name
    usage         = aws_dynamodb_table.usage.name
    prompt_cache  = aws_dynamodb_table.prompt_cache.name
    user_links    = var.enable_family_sharing ? aws_dynamodb_table.user_links[0].name : null
    consent_audit = var.gdpr_compliance_enabled ? aws_dynamodb_table.consent_audit[0].name : null
  }
}

output "dynamodb_table_arns" {
  description = "DynamoDB table ARNs"
  value = {
    user_data     = aws_dynamodb_table.user_data.arn
    subscriptions = aws_dynamodb_table.subscriptions.arn
    usage         = aws_dynamodb_table.usage.arn
    prompt_cache  = aws_dynamodb_table.prompt_cache.arn
    user_links    = var.enable_family_sharing ? aws_dynamodb_table.user_links[0].arn : null
    consent_audit = var.gdpr_compliance_enabled ? aws_dynamodb_table.consent_audit[0].arn : null
  }
}

# KMS Key Outputs
output "kms_key_ids" {
  description = "KMS key IDs for encryption"
  value = {
    dynamodb   = aws_kms_key.dynamodb.id
    lambda     = aws_kms_key.lambda.id
    s3         = aws_kms_key.s3.id
    cloudwatch = aws_kms_key.cloudwatch.id
    compliance = aws_kms_key.compliance.id
  }
  sensitive = true
}

output "kms_key_arns" {
  description = "KMS key ARNs for encryption"
  value = {
    dynamodb   = aws_kms_key.dynamodb.arn
    lambda     = aws_kms_key.lambda.arn
    s3         = aws_kms_key.s3.arn
    cloudwatch = aws_kms_key.cloudwatch.arn
    compliance = aws_kms_key.compliance.arn
  }
  sensitive = true
}

# IAM Role Outputs
output "iam_role_arns" {
  description = "IAM role ARNs"
  value = {
    lambda_execution         = aws_iam_role.lambda_execution.arn
    billing_lambda_execution = aws_iam_role.billing_lambda_execution.arn
    scheduler_lambda_execution = aws_iam_role.scheduler_lambda_execution.arn
    api_gateway_cloudwatch   = aws_iam_role.api_gateway_cloudwatch.arn
  }
}

# Monitoring Outputs
output "cloudwatch_dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}

output "sns_topic_arn" {
  description = "SNS topic ARN for alerts"
  value       = var.enable_sns_alerts ? aws_sns_topic.alerts[0].arn : null
}

# Security Outputs
output "waf_web_acl_arn" {
  description = "WAF Web ACL ARN for API Gateway"
  value       = var.enable_waf ? aws_wafv2_web_acl.api_gateway[0].arn : null
}

output "cloudfront_waf_web_acl_arn" {
  description = "WAF Web ACL ARN for CloudFront"
  value       = var.enable_cloudfront_waf ? aws_wafv2_web_acl.cloudfront[0].arn : null
}

# Custom Domain Outputs (if configured)
output "custom_domain_name" {
  description = "Custom domain name for API Gateway"
  value       = var.custom_domain_name != "" ? aws_api_gateway_domain_name.main[0].domain_name : null
}

# Lambda Function URLs (if enabled)
output "lambda_function_urls" {
  description = "Lambda function URLs for direct webhook access"
  value = var.enable_lambda_function_urls ? {
    universal_message_handler = aws_lambda_function_url.universal_message_handler[0].function_url
  } : null
}

# Environment Information
output "environment" {
  description = "Deployment environment"
  value       = var.environment
}

output "project_name" {
  description = "Project name"
  value       = var.project_name
}

output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

# Cost Optimization Information
output "cost_optimization_enabled" {
  description = "Whether cost optimization features are enabled"
  value       = var.enable_cost_optimization
}

output "prompt_cache_ttl" {
  description = "Prompt cache TTL in seconds"
  value       = var.prompt_cache_ttl
}

# Privacy and Compliance Information
output "gdpr_compliance_enabled" {
  description = "Whether GDPR compliance features are enabled"
  value       = var.gdpr_compliance_enabled
}

output "family_sharing_enabled" {
  description = "Whether family sharing features are enabled"
  value       = var.enable_family_sharing
}

# Deployment Information
output "deployment_timestamp" {
  description = "Infrastructure deployment timestamp"
  value       = timestamp()
}

# Resource Counts for Cost Estimation
output "resource_summary" {
  description = "Summary of deployed resources for cost estimation"
  value = {
    lambda_functions    = 3
    dynamodb_tables    = var.enable_family_sharing && var.gdpr_compliance_enabled ? 6 : (var.enable_family_sharing || var.gdpr_compliance_enabled ? 5 : 4)
    api_gateway_apis   = 1
    cloudfront_distributions = 1
    s3_buckets         = var.enable_cloudfront_logging ? 2 : 1
    kms_keys          = 5
    cloudwatch_alarms = length(aws_cloudwatch_metric_alarm.lambda_errors) + length(aws_cloudwatch_metric_alarm.lambda_duration) + length(aws_cloudwatch_metric_alarm.dynamodb_throttles) + 1
  }
}
