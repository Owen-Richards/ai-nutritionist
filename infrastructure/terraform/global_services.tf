# Global Services for International Deployment
# AWS services for comprehensive international support

# ===== TRANSLATION & LANGUAGE SERVICES =====
# Note: Amazon Translate resources are managed through API calls, not Terraform resources
# S3 buckets for translation input/output

resource "aws_s3_bucket" "translation_input" {
  count  = var.enable_translation ? 1 : 0
  bucket = "${var.project_name}-translation-input-${var.environment}-${random_string.bucket_suffix.result}"

  tags = merge(
    {
      Name    = "${var.project_name}-translation-input-${var.environment}"
      Purpose = "Translation service input"
    },
    var.additional_tags
  )
}

resource "aws_s3_bucket" "translation_output" {
  count  = var.enable_translation ? 1 : 0
  bucket = "${var.project_name}-translation-output-${var.environment}-${random_string.bucket_suffix.result}"

  tags = merge(
    {
      Name    = "${var.project_name}-translation-output-${var.environment}"
      Purpose = "Translation service output"
    },
    var.additional_tags
  )
}

# ===== TEXT-TO-SPEECH & VOICE SERVICES =====
# Note: Amazon Polly resources are managed through API calls
# Lexicon files stored in S3 for custom pronunciation

resource "aws_s3_bucket" "polly_lexicons" {
  count  = var.enable_polly ? 1 : 0
  bucket = "${var.project_name}-polly-lexicons-${var.environment}-${random_string.bucket_suffix.result}"

  tags = merge(
    {
      Name    = "${var.project_name}-polly-lexicons-${var.environment}"
      Purpose = "Polly lexicon storage"
    },
    var.additional_tags
  )
}

# ===== NATURAL LANGUAGE PROCESSING =====

# S3 bucket for Comprehend training data
resource "aws_s3_bucket" "comprehend_training" {
  count  = var.enable_comprehend ? 1 : 0
  bucket = "${var.project_name}-comprehend-training-${var.environment}-${random_string.bucket_suffix.result}"

  tags = merge(
    {
      Name    = "${var.project_name}-comprehend-training-${var.environment}"
      Purpose = "Comprehend model training data"
    },
    var.additional_tags
  )
}

# ===== MULTI-REGION DEPLOYMENT =====

# Global DynamoDB tables with Global Tables
resource "aws_dynamodb_table" "user_profiles_global" {
  count          = var.enable_global_tables ? 1 : 0
  name           = "${var.project_name}-user-profiles-global-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "user_id"
  stream_enabled = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  attribute {
    name = "user_id"
    type = "S"
  }

  replica {
    region_name = "us-east-1"
  }

  replica {
    region_name = "eu-west-1"
  }

  replica {
    region_name = "ap-southeast-1"
  }

  tags = merge(
    {
      Name    = "${var.project_name}-user-profiles-global-${var.environment}"
      Purpose = "Global user profiles with multi-region replication"
    },
    var.additional_tags
  )
}

# CloudFront with multiple origins for global content delivery
resource "aws_cloudfront_distribution" "global_api" {
  count = var.enable_global_cloudfront ? 1 : 0

  # Multiple origins for different regions
  dynamic "origin" {
    for_each = var.api_gateway_regions
    content {
      domain_name = "${aws_api_gateway_rest_api.main.id}.execute-api.${origin.value}.amazonaws.com"
      origin_id   = "api-${origin.value}"
      
      custom_origin_config {
        http_port              = 443
        https_port             = 443
        origin_protocol_policy = "https-only"
        origin_ssl_protocols   = ["TLSv1.2"]
      }
    }
  }

  enabled = true
  
  # Geographic restrictions can be configured
  restrictions {
    geo_restriction {
      restriction_type = var.geo_restriction_type
      locations        = var.geo_restriction_countries
    }
  }

  # Cache behaviors for different regions
  default_cache_behavior {
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "api-${var.primary_region}"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Accept-Language", "CloudFront-Viewer-Country"]
      
      cookies {
        forward = "none"
      }
    }

    # TTL settings for global content
    min_ttl     = 0
    default_ttl = 300
    max_ttl     = 86400
  }

  viewer_certificate {
    cloudfront_default_certificate = true
    minimum_protocol_version       = "TLSv1.2_2021"
  }

  tags = merge(
    {
      Name    = "${var.project_name}-global-api-${var.environment}"
      Purpose = "Global API distribution"
    },
    var.additional_tags
  )
}

# ===== REGIONAL COMPLIANCE & DATA RESIDENCY =====

# KMS keys for different regions to support data residency
resource "aws_kms_key" "regional_encryption" {
  for_each = var.enable_regional_encryption ? toset(var.compliance_regions) : toset([])
  
  provider                = aws.region[each.key]
  description             = "Regional encryption key for ${each.key} - ${var.project_name} ${var.environment}"
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
      }
    ]
  })

  tags = merge(
    {
      Name    = "${var.project_name}-regional-key-${each.key}-${var.environment}"
      Purpose = "Regional data encryption for compliance"
      Region  = each.key
    },
    var.additional_tags
  )
}

# ===== CULTURAL & DIETARY SERVICES =====

# Parameter Store for cultural configurations
resource "aws_ssm_parameter" "cultural_dietary_restrictions" {
  for_each = var.enable_cultural_support ? var.cultural_configs : {}
  
  name  = "/${var.project_name}/${var.environment}/cultural/${each.key}/dietary_restrictions"
  type  = "String"
  value = jsonencode(each.value.dietary_restrictions)

  tags = merge(
    {
      Name    = "${var.project_name}-cultural-${each.key}-${var.environment}"
      Purpose = "Cultural dietary restrictions"
      Culture = each.key
    },
    var.additional_tags
  )
}

resource "aws_ssm_parameter" "cultural_food_preferences" {
  for_each = var.enable_cultural_support ? var.cultural_configs : {}
  
  name  = "/${var.project_name}/${var.environment}/cultural/${each.key}/food_preferences"
  type  = "String"
  value = jsonencode(each.value.food_preferences)

  tags = merge(
    {
      Name    = "${var.project_name}-cultural-food-${each.key}-${var.environment}"
      Purpose = "Cultural food preferences"
      Culture = each.key
    },
    var.additional_tags
  )
}

# ===== GLOBAL MONITORING & ANALYTICS =====

# CloudWatch custom metrics for global usage
resource "aws_cloudwatch_metric_alarm" "global_api_latency" {
  count = var.enable_global_monitoring ? length(var.global_table_regions) : 0
  
  alarm_name          = "${var.project_name}-global-api-latency-${var.global_table_regions[count.index]}-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = "5000"
  alarm_description   = "This metric monitors lambda duration in ${var.global_table_regions[count.index]}"

  dimensions = {
    FunctionName = "${var.project_name}-universal-handler-${var.global_table_regions[count.index]}-${var.environment}"
  }

  alarm_actions = [aws_sns_topic.global_alerts[0].arn]

  tags = merge(
    {
      Name    = "${var.project_name}-global-latency-${var.global_table_regions[count.index]}-${var.environment}"
      Purpose = "Global API latency monitoring"
      Region  = var.global_table_regions[count.index]
    },
    var.additional_tags
  )
}

resource "aws_sns_topic" "global_alerts" {
  count = var.enable_global_monitoring ? 1 : 0
  name  = "${var.project_name}-global-alerts-${var.environment}"

  tags = merge(
    {
      Name    = "${var.project_name}-global-alerts-${var.environment}"
      Purpose = "Global monitoring alerts"
    },
    var.additional_tags
  )
}

# ===== HELPER RESOURCES =====

resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

# Data source for current AWS account
data "aws_caller_identity" "current" {}
