# KMS Keys for Encryption

# Primary KMS key for DynamoDB encryption
resource "aws_kms_key" "dynamodb" {
  description             = "KMS key for DynamoDB encryption - ${var.project_name} ${var.environment}"
  deletion_window_in_days = var.environment == "prod" ? 30 : 7
  enable_key_rotation     = true

  tags = merge(
    {
      Name    = "${var.project_name}-dynamodb-key-${var.environment}"
      Purpose = "DynamoDB encryption"
      Service = "DynamoDB"
    },
    var.additional_tags
  )
}

resource "aws_kms_alias" "dynamodb" {
  name          = "alias/${var.project_name}-dynamodb-${var.environment}"
  target_key_id = aws_kms_key.dynamodb.key_id
}

# KMS key for compliance and audit data
resource "aws_kms_key" "compliance" {
  count = var.gdpr_compliance_enabled ? 1 : 0
  
  description             = "KMS key for compliance data encryption - ${var.project_name} ${var.environment}"
  deletion_window_in_days = 30 # Always use longer retention for compliance
  enable_key_rotation     = true

  # Enhanced security for compliance data
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
        Sid    = "Allow CloudWatch Logs"
        Effect = "Allow"
        Principal = {
          Service = "logs.${var.aws_region}.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(
    {
      Name        = "${var.project_name}-compliance-key-${var.environment}"
      Purpose     = "Compliance and audit data encryption"
      Compliance  = "GDPR"
      DataClass   = "HighSensitivity"
    },
    var.additional_tags
  )
}

resource "aws_kms_alias" "compliance" {
  count = var.gdpr_compliance_enabled ? 1 : 0
  
  name          = "alias/${var.project_name}-compliance-${var.environment}"
  target_key_id = aws_kms_key.compliance[0].key_id
}

# KMS key for Lambda environment variables
resource "aws_kms_key" "lambda" {
  description             = "KMS key for Lambda environment variables - ${var.project_name} ${var.environment}"
  deletion_window_in_days = var.environment == "prod" ? 30 : 7
  enable_key_rotation     = true

  tags = merge(
    {
      Name    = "${var.project_name}-lambda-key-${var.environment}"
      Purpose = "Lambda environment variable encryption"
      Service = "Lambda"
    },
    var.additional_tags
  )
}

resource "aws_kms_alias" "lambda" {
  name          = "alias/${var.project_name}-lambda-${var.environment}"
  target_key_id = aws_kms_key.lambda.key_id
}

# KMS key for S3 bucket encryption
resource "aws_kms_key" "s3" {
  description             = "KMS key for S3 bucket encryption - ${var.project_name} ${var.environment}"
  deletion_window_in_days = var.environment == "prod" ? 30 : 7
  enable_key_rotation     = true

  tags = merge(
    {
      Name    = "${var.project_name}-s3-key-${var.environment}"
      Purpose = "S3 bucket encryption"
      Service = "S3"
    },
    var.additional_tags
  )
}

resource "aws_kms_alias" "s3" {
  name          = "alias/${var.project_name}-s3-${var.environment}"
  target_key_id = aws_kms_key.s3.key_id
}

# KMS key for CloudWatch Logs encryption
resource "aws_kms_key" "cloudwatch" {
  description             = "KMS key for CloudWatch Logs encryption - ${var.project_name} ${var.environment}"
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
        Sid    = "Allow CloudWatch Logs"
        Effect = "Allow"
        Principal = {
          Service = "logs.${var.aws_region}.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          ArnEquals = {
            "kms:EncryptionContext:aws:logs:arn" = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.project_name}-*"
          }
        }
      }
    ]
  })

  tags = merge(
    {
      Name    = "${var.project_name}-cloudwatch-key-${var.environment}"
      Purpose = "CloudWatch Logs encryption"
      Service = "CloudWatch"
    },
    var.additional_tags
  )
}

resource "aws_kms_alias" "cloudwatch" {
  name          = "alias/${var.project_name}-cloudwatch-${var.environment}"
  target_key_id = aws_kms_key.cloudwatch.key_id
}
