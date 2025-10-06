# AWS Config for Compliance and Security Monitoring
# AWS Config tracks configuration changes and compliance

resource "aws_config_configuration_recorder" "main" {
  count = var.enable_aws_config ? 1 : 0
  
  name     = "${var.project_name}-config-recorder-${var.environment}"
  role_arn = aws_iam_role.config[0].arn

  recording_group {
    all_supported                 = true
    include_global_resource_types = true
  }

  depends_on = [aws_config_delivery_channel.main]
}

resource "aws_config_delivery_channel" "main" {
  count = var.enable_aws_config ? 1 : 0
  
  name           = "${var.project_name}-config-delivery-${var.environment}"
  s3_bucket_name = aws_s3_bucket.config[0].bucket
  s3_key_prefix  = "config"

  snapshot_delivery_properties {
    delivery_frequency = "TwentyFour_Hours"
  }
}

# S3 Bucket for AWS Config
resource "aws_s3_bucket" "config" {
  count = var.enable_aws_config ? 1 : 0
  
  bucket        = "${var.project_name}-aws-config-${var.environment}-${random_string.config_bucket_suffix[0].result}"
  force_destroy = var.environment != "prod"

  tags = merge(
    {
      Name    = "${var.project_name}-aws-config-${var.environment}"
      Purpose = "AWS Config compliance monitoring"
    },
    var.additional_tags
  )
}

resource "random_string" "config_bucket_suffix" {
  count = var.enable_aws_config ? 1 : 0
  
  length  = 8
  special = false
  upper   = false
}

# Config Bucket Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "config" {
  count = var.enable_aws_config ? 1 : 0
  
  bucket = aws_s3_bucket.config[0].id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

# Config Bucket Policy
resource "aws_s3_bucket_policy" "config" {
  count = var.enable_aws_config ? 1 : 0
  
  bucket = aws_s3_bucket.config[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AWSConfigBucketPermissionsCheck"
        Effect = "Allow"
        Principal = {
          Service = "config.amazonaws.com"
        }
        Action   = "s3:GetBucketAcl"
        Resource = aws_s3_bucket.config[0].arn
        Condition = {
          StringEquals = {
            "AWS:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      },
      {
        Sid    = "AWSConfigBucketExistenceCheck"
        Effect = "Allow"
        Principal = {
          Service = "config.amazonaws.com"
        }
        Action   = "s3:ListBucket"
        Resource = aws_s3_bucket.config[0].arn
        Condition = {
          StringEquals = {
            "AWS:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      },
      {
        Sid    = "AWSConfigBucketDelivery"
        Effect = "Allow"
        Principal = {
          Service = "config.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.config[0].arn}/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-acl"     = "bucket-owner-full-control"
            "AWS:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
}

# AWS Config IAM Role
resource "aws_iam_role" "config" {
  count = var.enable_aws_config ? 1 : 0
  
  name = "${var.project_name}-config-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "config.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    {
      Name = "${var.project_name}-config-role-${var.environment}"
    },
    var.additional_tags
  )
}

resource "aws_iam_role_policy_attachment" "config" {
  count = var.enable_aws_config ? 1 : 0
  
  role       = aws_iam_role.config[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/ConfigRole"
}

# AWS GuardDuty for Threat Detection
resource "aws_guardduty_detector" "main" {
  count = var.enable_guardduty ? 1 : 0
  
  enable                       = true
  finding_publishing_frequency = "FIFTEEN_MINUTES"

  tags = merge(
    {
      Name = "${var.project_name}-guardduty-${var.environment}"
    },
    var.additional_tags
  )
}

# GuardDuty CloudWatch Event Rule for High/Medium Findings
resource "aws_cloudwatch_event_rule" "guardduty_findings" {
  count = var.enable_guardduty ? 1 : 0
  
  name        = "${var.project_name}-guardduty-findings-${var.environment}"
  description = "Capture GuardDuty findings"

  event_pattern = jsonencode({
    source      = ["aws.guardduty"]
    detail-type = ["GuardDuty Finding"]
    detail = {
      severity = [
        { numeric = [">", 4.0] }  # Medium and High severity
      ]
    }
  })

  tags = merge(
    {
      Name = "${var.project_name}-guardduty-rule-${var.environment}"
    },
    var.additional_tags
  )
}

# GuardDuty SNS Topic for Alerts
resource "aws_sns_topic" "guardduty_alerts" {
  count = var.enable_guardduty && var.enable_sns_alerts ? 1 : 0
  
  name         = "${var.project_name}-guardduty-alerts-${var.environment}"
  display_name = "GuardDuty Security Alerts"

  kms_master_key_id = aws_kms_key.cloudwatch.arn

  tags = merge(
    {
      Name = "${var.project_name}-guardduty-alerts-${var.environment}"
    },
    var.additional_tags
  )
}

# GuardDuty EventBridge Target
resource "aws_cloudwatch_event_target" "guardduty_sns" {
  count = var.enable_guardduty && var.enable_sns_alerts ? 1 : 0
  
  rule      = aws_cloudwatch_event_rule.guardduty_findings[0].name
  target_id = "GuardDutySNSTarget"
  arn       = aws_sns_topic.guardduty_alerts[0].arn

  input_transformer {
    input_paths = {
      severity    = "$.detail.severity"
      title       = "$.detail.title"
      description = "$.detail.description"
      region      = "$.detail.region"
      account     = "$.detail.accountId"
    }
    input_template = jsonencode({
      severity    = "<severity>"
      title       = "<title>"
      description = "<description>"
      region      = "<region>"
      account     = "<account>"
      timestamp   = "$${aws.events.event.ingestion-time}"
    })
  }
}

# Security Hub for Centralized Security Findings
resource "aws_securityhub_account" "main" {
  count = var.enable_security_hub ? 1 : 0
  
  enable_default_standards = true

  control_finding_generator = "SECURITY_CONTROL"
  auto_enable_controls      = true
}

# Enable AWS Foundational Security Standard
resource "aws_securityhub_standards_subscription" "aws_foundational" {
  count = var.enable_security_hub ? 1 : 0
  
  standards_arn = "arn:aws:securityhub:::ruleset/finding-format/aws-foundational-security-standard/v/1.0.0"
  
  depends_on = [aws_securityhub_account.main]
}

# Enable CIS AWS Foundations Benchmark
resource "aws_securityhub_standards_subscription" "cis" {
  count = var.enable_security_hub ? 1 : 0
  
  standards_arn = "arn:aws:securityhub:::ruleset/finding-format/cis-aws-foundations-benchmark/v/1.2.0"
  
  depends_on = [aws_securityhub_account.main]
}

# AWS Config Rules for Compliance
resource "aws_config_config_rule" "s3_bucket_public_read_prohibited" {
  count = var.enable_aws_config ? 1 : 0
  
  name = "${var.project_name}-s3-bucket-public-read-prohibited-${var.environment}"

  source {
    owner             = "AWS"
    source_identifier = "S3_BUCKET_PUBLIC_READ_PROHIBITED"
  }

  depends_on = [aws_config_configuration_recorder.main]
}

resource "aws_config_config_rule" "s3_bucket_ssl_requests_only" {
  count = var.enable_aws_config ? 1 : 0
  
  name = "${var.project_name}-s3-bucket-ssl-requests-only-${var.environment}"

  source {
    owner             = "AWS"
    source_identifier = "S3_BUCKET_SSL_REQUESTS_ONLY"
  }

  depends_on = [aws_config_configuration_recorder.main]
}

resource "aws_config_config_rule" "lambda_function_settings_check" {
  count = var.enable_aws_config ? 1 : 0
  
  name = "${var.project_name}-lambda-function-settings-check-${var.environment}"

  source {
    owner             = "AWS"
    source_identifier = "LAMBDA_FUNCTION_SETTINGS_CHECK"
  }

  input_parameters = jsonencode({
    runtime        = var.lambda_runtime
    memorySize     = var.lambda_memory_size
    timeout        = var.lambda_timeout
  })

  depends_on = [aws_config_configuration_recorder.main]
}
