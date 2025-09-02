# IAM Roles and Policies for Lambda Functions

# Lambda execution role for universal message handler
resource "aws_iam_role" "lambda_execution" {
  name = "${var.project_name}-lambda-execution-${var.environment}"

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
      Name    = "${var.project_name}-lambda-execution-${var.environment}"
      Purpose = "Lambda execution role"
    },
    var.additional_tags
  )
}

# Lambda execution policy
resource "aws_iam_role_policy" "lambda_execution" {
  name = "${var.project_name}-lambda-execution-policy-${var.environment}"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # CloudWatch Logs
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.project_name}-*"
      },
      # DynamoDB access
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
        Resource = [
          aws_dynamodb_table.user_data.arn,
          aws_dynamodb_table.subscriptions.arn,
          aws_dynamodb_table.usage.arn,
          aws_dynamodb_table.prompt_cache.arn,
          "${aws_dynamodb_table.user_data.arn}/index/*",
          "${aws_dynamodb_table.subscriptions.arn}/index/*",
          "${aws_dynamodb_table.usage.arn}/index/*",
          "${aws_dynamodb_table.prompt_cache.arn}/index/*"
        ]
      },
      # Family sharing tables (conditional)
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
        Resource = var.enable_family_sharing ? [
          aws_dynamodb_table.user_links[0].arn,
          "${aws_dynamodb_table.user_links[0].arn}/index/*"
        ] : []
      },
      # GDPR audit table (conditional)
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:Query"
        ]
        Resource = var.gdpr_compliance_enabled ? [
          aws_dynamodb_table.consent_audit[0].arn,
          "${aws_dynamodb_table.consent_audit[0].arn}/index/*"
        ] : []
      },
      # Bedrock AI access
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          for model in var.bedrock_models :
          "arn:aws:bedrock:${var.aws_region}::foundation-model/${model}"
        ]
      },
      # SSM Parameter Store access
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${var.project_name}/*"
      },
      # Secrets Manager access
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/*"
      },
      # KMS access for encryption
      {
        Effect = "Allow"
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = [
          aws_kms_key.lambda.arn,
          aws_kms_key.cloudwatch.arn
        ]
      }
    ]
  })
}

# VPC execution policy (conditional)
resource "aws_iam_role_policy_attachment" "lambda_vpc_execution" {
  count = var.enable_vpc ? 1 : 0
  
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# X-Ray tracing policy (conditional)
resource "aws_iam_role_policy_attachment" "lambda_xray_tracing" {
  count = var.enable_xray_tracing ? 1 : 0
  
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# Separate role for billing webhook function (least privilege)
resource "aws_iam_role" "billing_lambda_execution" {
  name = "${var.project_name}-billing-lambda-${var.environment}"

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
      Name    = "${var.project_name}-billing-lambda-${var.environment}"
      Purpose = "Billing webhook lambda execution role"
    },
    var.additional_tags
  )
}

# Billing lambda policy (restricted access)
resource "aws_iam_role_policy" "billing_lambda_execution" {
  name = "${var.project_name}-billing-lambda-policy-${var.environment}"
  role = aws_iam_role.billing_lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # CloudWatch Logs
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.project_name}-billing-*"
      },
      # Limited DynamoDB access for subscriptions only
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem"
        ]
        Resource = aws_dynamodb_table.subscriptions.arn
      },
      # SSM Parameter Store access for Stripe secrets
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter"
        ]
        Resource = [
          "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${var.project_name}/stripe/*"
        ]
      }
    ]
  })
}

# Scheduler lambda role
resource "aws_iam_role" "scheduler_lambda_execution" {
  name = "${var.project_name}-scheduler-lambda-${var.environment}"

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
      Name    = "${var.project_name}-scheduler-lambda-${var.environment}"
      Purpose = "Scheduler lambda execution role"
    },
    var.additional_tags
  )
}

# Scheduler lambda policy
resource "aws_iam_role_policy" "scheduler_lambda_execution" {
  name = "${var.project_name}-scheduler-lambda-policy-${var.environment}"
  role = aws_iam_role.scheduler_lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # CloudWatch Logs
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.project_name}-scheduler-*"
      },
      # DynamoDB access for reading users and writing meal plans
      {
        Effect = "Allow"
        Action = [
          "dynamodb:Scan",
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem"
        ]
        Resource = [
          aws_dynamodb_table.user_data.arn,
          aws_dynamodb_table.prompt_cache.arn
        ]
      },
      # Bedrock AI access for meal plan generation
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.titan-text-express-v1"
      },
      # SSM Parameter Store access
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${var.project_name}/*"
      }
    ]
  })
}

# API Gateway CloudWatch role
resource "aws_iam_role" "api_gateway_cloudwatch" {
  name = "${var.project_name}-api-gateway-cloudwatch-${var.environment}"

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

  tags = merge(
    {
      Name    = "${var.project_name}-api-gateway-cloudwatch-${var.environment}"
      Purpose = "API Gateway CloudWatch logging role"
    },
    var.additional_tags
  )
}

# API Gateway CloudWatch policy
resource "aws_iam_role_policy_attachment" "api_gateway_cloudwatch" {
  role       = aws_iam_role.api_gateway_cloudwatch.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}
