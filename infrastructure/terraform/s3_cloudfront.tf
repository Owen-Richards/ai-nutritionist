# S3 Bucket for Web Frontend
resource "aws_s3_bucket" "web_frontend" {
  bucket = "${var.project_name}-web-frontend-${var.environment}-${random_string.bucket_suffix.result}"

  tags = merge(
    {
      Name    = "${var.project_name}-web-frontend-${var.environment}"
      Purpose = "Static website hosting for AI Nutritionist frontend"
    },
    var.additional_tags
  )
}

# Random string for bucket name uniqueness
resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

# S3 Bucket Versioning
resource "aws_s3_bucket_versioning" "web_frontend" {
  bucket = aws_s3_bucket.web_frontend.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Bucket Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "web_frontend" {
  bucket = aws_s3_bucket.web_frontend.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

# S3 Bucket Public Access Block
resource "aws_s3_bucket_public_access_block" "web_frontend" {
  bucket = aws_s3_bucket.web_frontend.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket Policy for CloudFront Access
resource "aws_s3_bucket_policy" "web_frontend" {
  bucket = aws_s3_bucket.web_frontend.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontServicePrincipal"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.web_frontend.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.web_frontend.arn
          }
        }
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.web_frontend]
}

# Upload index.html to S3
resource "aws_s3_object" "index_html" {
  bucket       = aws_s3_bucket.web_frontend.id
  key          = "index.html"
  source       = "${path.module}/../../src/web/index.html"
  content_type = "text/html"
  etag         = filemd5("${path.module}/../../src/web/index.html")

  server_side_encryption = "aws:kms"
  kms_key_id            = aws_kms_key.s3.arn

  tags = merge(
    {
      Name = "index.html"
    },
    var.additional_tags
  )
}

# CloudFront Origin Access Control
resource "aws_cloudfront_origin_access_control" "web_frontend" {
  name                              = "${var.project_name}-oac-${var.environment}"
  description                       = "OAC for AI Nutritionist web frontend"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# CloudFront Distribution
resource "aws_cloudfront_distribution" "web_frontend" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  price_class         = var.cloudfront_price_class

  origin {
    domain_name              = aws_s3_bucket.web_frontend.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.web_frontend.id
    origin_id                = "S3-${aws_s3_bucket.web_frontend.id}"
  }

  # API Gateway origin for backend requests
  origin {
    domain_name = "${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com"
    origin_id   = "APIGateway"
    origin_path = "/${var.environment}"

    custom_origin_config {
      http_port              = 443
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # Default cache behavior for static content
  default_cache_behavior {
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${aws_s3_bucket.web_frontend.id}"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = var.cloudfront_default_ttl
    max_ttl     = var.cloudfront_max_ttl
  }

  # Cache behavior for API requests
  ordered_cache_behavior {
    path_pattern           = "/webhook*"
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD", "OPTIONS"]
    target_origin_id       = "APIGateway"
    compress               = false
    viewer_protocol_policy = "https-only"

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "X-Twilio-Signature", "Content-Type"]
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  # Cache behavior for billing webhooks
  ordered_cache_behavior {
    path_pattern           = "/billing*"
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD", "OPTIONS"]
    target_origin_id       = "APIGateway"
    compress               = false
    viewer_protocol_policy = "https-only"

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Stripe-Signature", "Content-Type"]
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  # Geographic restrictions (optional)
  dynamic "restrictions" {
    for_each = length(var.cloudfront_geo_restrictions) > 0 ? [1] : []
    content {
      geo_restriction {
        restriction_type = var.cloudfront_geo_restriction_type
        locations        = var.cloudfront_geo_restrictions
      }
    }
  }

  # SSL Certificate
  viewer_certificate {
    acm_certificate_arn      = var.cloudfront_ssl_certificate_arn != "" ? var.cloudfront_ssl_certificate_arn : null
    ssl_support_method       = var.cloudfront_ssl_certificate_arn != "" ? "sni-only" : null
    minimum_protocol_version = var.cloudfront_ssl_certificate_arn != "" ? "TLSv1.2_2021" : null
    cloudfront_default_certificate = var.cloudfront_ssl_certificate_arn == "" ? true : null
  }

  # Custom error pages
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }

  # WAF Web ACL association (optional)
  dynamic "web_acl_id" {
    for_each = var.enable_cloudfront_waf ? [aws_wafv2_web_acl.cloudfront[0].arn] : []
    content {
      web_acl_id = web_acl_id.value
    }
  }

  # Logging configuration (optional)
  dynamic "logging_config" {
    for_each = var.enable_cloudfront_logging ? [1] : []
    content {
      bucket          = aws_s3_bucket.cloudfront_logs[0].bucket_domain_name
      prefix          = "cloudfront-logs/"
      include_cookies = false
    }
  }

  tags = merge(
    {
      Name = "${var.project_name}-cloudfront-${var.environment}"
    },
    var.additional_tags
  )
}

# S3 Bucket for CloudFront Logs (optional)
resource "aws_s3_bucket" "cloudfront_logs" {
  count = var.enable_cloudfront_logging ? 1 : 0
  
  bucket = "${var.project_name}-cloudfront-logs-${var.environment}-${random_string.logs_bucket_suffix[0].result}"

  tags = merge(
    {
      Name    = "${var.project_name}-cloudfront-logs-${var.environment}"
      Purpose = "CloudFront access logs"
    },
    var.additional_tags
  )
}

resource "random_string" "logs_bucket_suffix" {
  count = var.enable_cloudfront_logging ? 1 : 0
  
  length  = 8
  special = false
  upper   = false
}

# CloudFront Logs Bucket Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "cloudfront_logs" {
  count = var.enable_cloudfront_logging ? 1 : 0
  
  bucket = aws_s3_bucket.cloudfront_logs[0].id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

# CloudFront Logs Bucket Lifecycle
resource "aws_s3_bucket_lifecycle_configuration" "cloudfront_logs" {
  count = var.enable_cloudfront_logging ? 1 : 0
  
  bucket = aws_s3_bucket.cloudfront_logs[0].id

  rule {
    id     = "delete_old_logs"
    status = "Enabled"

    expiration {
      days = var.cloudfront_logs_retention_days
    }

    noncurrent_version_expiration {
      noncurrent_days = 1
    }
  }
}

# WAF for CloudFront (optional)
resource "aws_wafv2_web_acl" "cloudfront" {
  count = var.enable_cloudfront_waf ? 1 : 0
  
  name  = "${var.project_name}-cloudfront-waf-${var.environment}"
  scope = "CLOUDFRONT"

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
        limit              = var.cloudfront_waf_rate_limit
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.project_name}-cf-rate-limit-${var.environment}"
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
      metric_name                = "${var.project_name}-cf-common-rules-${var.environment}"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.project_name}-cf-waf-${var.environment}"
    sampled_requests_enabled   = true
  }

  tags = merge(
    {
      Name = "${var.project_name}-cloudfront-waf-${var.environment}"
    },
    var.additional_tags
  )
}
