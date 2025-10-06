# IAM Roles and Policies for Global Services
# Additional IAM configurations for international deployment

# ===== TRANSLATION SERVICE IAM =====

resource "aws_iam_role" "translate_service" {
  count = var.enable_translation ? 1 : 0
  name  = "${var.project_name}-translate-service-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "translate.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    {
      Name    = "${var.project_name}-translate-service-${var.environment}"
      Purpose = "Translation service execution role"
    },
    var.additional_tags
  )
}

resource "aws_iam_role_policy" "translate_service" {
  count = var.enable_translation ? 1 : 0
  name  = "${var.project_name}-translate-service-${var.environment}"
  role  = aws_iam_role.translate_service[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.translation_input[0].arn,
          "${aws_s3_bucket.translation_input[0].arn}/*",
          aws_s3_bucket.translation_output[0].arn,
          "${aws_s3_bucket.translation_output[0].arn}/*"
        ]
      }
    ]
  })
}

# ===== COMPREHEND SERVICE IAM =====

resource "aws_iam_role" "comprehend_service" {
  count = var.enable_comprehend ? 1 : 0
  name  = "${var.project_name}-comprehend-service-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "comprehend.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    {
      Name    = "${var.project_name}-comprehend-service-${var.environment}"
      Purpose = "Comprehend service execution role"
    },
    var.additional_tags
  )
}

resource "aws_iam_role_policy" "comprehend_service" {
  count = var.enable_comprehend ? 1 : 0
  name  = "${var.project_name}-comprehend-service-${var.environment}"
  role  = aws_iam_role.comprehend_service[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.comprehend_training[0].arn,
          "${aws_s3_bucket.comprehend_training[0].arn}/*"
        ]
      }
    ]
  })
}

# ===== LAMBDA GLOBAL EXECUTION ROLE =====

resource "aws_iam_role" "lambda_global_execution" {
  count = var.enable_global_tables ? 1 : 0
  name  = "${var.project_name}-lambda-global-execution-${var.environment}"

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

  tags = merge(
    {
      Name    = "${var.project_name}-lambda-global-execution-${var.environment}"
      Purpose = "Lambda execution role for global services"
    },
    var.additional_tags
  )
}

resource "aws_iam_role_policy_attachment" "lambda_global_basic" {
  count      = var.enable_global_tables ? 1 : 0
  role       = aws_iam_role.lambda_global_execution[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_global_permissions" {
  count = var.enable_global_tables ? 1 : 0
  name  = "${var.project_name}-lambda-global-permissions-${var.environment}"
  role  = aws_iam_role.lambda_global_execution[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = "arn:aws:dynamodb:*:*:table/${var.project_name}-*"
      },
      {
        Effect = "Allow"
        Action = [
          "translate:TranslateText",
          "translate:DescribeTextTranslationJob",
          "translate:StartTextTranslationJob"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:RequestedRegion" = var.global_table_regions
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "polly:SynthesizeSpeech",
          "polly:DescribeVoices"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "comprehend:DetectDominantLanguage",
          "comprehend:DetectSentiment",
          "comprehend:DetectEntities"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = "arn:aws:ssm:*:*:parameter/${var.project_name}/*"
      }
    ]
  })
}

# ===== GLOBAL CLOUDFRONT ORIGIN ACCESS CONTROL =====

resource "aws_cloudfront_origin_access_control" "global_api" {
  count                             = var.enable_global_cloudfront ? 1 : 0
  name                              = "${var.project_name}-global-api-oac-${var.environment}"
  description                       = "Origin Access Control for global API distribution"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# ===== REGIONAL PROVIDER CONFIGURATIONS =====

# Configure providers for multi-region deployment
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

provider "aws" {
  alias  = "eu_west_1"
  region = "eu-west-1"
}

provider "aws" {
  alias  = "ap_southeast_1"
  region = "ap-southeast-1"
}

provider "aws" {
  alias  = "ap_northeast_1"
  region = "ap-northeast-1"
}

# ===== CROSS-REGION REPLICATION IAM =====

resource "aws_iam_role" "cross_region_replication" {
  count = var.enable_global_tables ? 1 : 0
  name  = "${var.project_name}-cross-region-replication-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    {
      Name    = "${var.project_name}-cross-region-replication-${var.environment}"
      Purpose = "Cross-region S3 replication role"
    },
    var.additional_tags
  )
}

resource "aws_iam_role_policy" "cross_region_replication" {
  count = var.enable_global_tables ? 1 : 0
  name  = "${var.project_name}-cross-region-replication-${var.environment}"
  role  = aws_iam_role.cross_region_replication[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObjectVersionForReplication",
          "s3:GetObjectVersionAcl",
          "s3:GetObjectVersionTagging"
        ]
        Resource = "arn:aws:s3:::${var.project_name}-*/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = "arn:aws:s3:::${var.project_name}-*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ReplicateObject",
          "s3:ReplicateDelete",
          "s3:ReplicateTags"
        ]
        Resource = "arn:aws:s3:::${var.project_name}-*/*"
      }
    ]
  })
}
