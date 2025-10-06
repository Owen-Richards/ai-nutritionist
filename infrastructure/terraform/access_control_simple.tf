# 🛡️ SIMPLIFIED ACCESS CONTROL (Fixed for Terraform)
# Using only standard AWS provider resources

# ===== AUTHORIZED USERS TABLE =====

resource "aws_dynamodb_table" "authorized_users" {
  name           = "${var.project_name}-authorized-users-${var.environment}"
  billing_mode   = var.testing_mode ? "PAY_PER_REQUEST" : "PROVISIONED"
  read_capacity  = var.testing_mode ? null : 5
  write_capacity = var.testing_mode ? null : 5
  hash_key       = "phone_number"

  attribute {
    name = "phone_number"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name            = "UserIdIndex"
    hash_key        = "user_id"
    projection_type = "ALL"
    read_capacity   = var.testing_mode ? null : 5
    write_capacity  = var.testing_mode ? null : 5
  }

  global_secondary_index {
    name            = "StatusIndex"
    hash_key        = "status"
    projection_type = "ALL"
    read_capacity   = var.testing_mode ? null : 5
    write_capacity  = var.testing_mode ? null : 5
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = merge(
    {
      Name    = "${var.project_name}-authorized-users-${var.environment}"
      Purpose = "User access control and whitelisting"
    },
    var.additional_tags
  )
}

# ===== USAGE TRACKING TABLE =====

resource "aws_dynamodb_table" "usage_tracking" {
  name           = "${var.project_name}-usage-tracking-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "phone_number"
  range_key      = "date"

  attribute {
    name = "phone_number"
    type = "S"
  }

  attribute {
    name = "date"
    type = "S"
  }

  attribute {
    name = "month"
    type = "S"
  }

  global_secondary_index {
    name            = "MonthlyUsageIndex"
    hash_key        = "month"
    range_key       = "phone_number"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = merge(
    {
      Name    = "${var.project_name}-usage-tracking-${var.environment}"
      Purpose = "Track user usage for rate limiting"
    },
    var.additional_tags
  )
}

# ===== LAMBDA AUTHORIZATION FUNCTION =====

resource "aws_lambda_function" "authorizer" {
  filename         = data.archive_file.authorizer_zip.output_path
  function_name    = "${var.project_name}-authorizer-${var.environment}"
  role            = aws_iam_role.authorizer_role.arn
  handler         = "authorization.lambda_handler"
  runtime         = "python3.11"
  timeout         = 30
  memory_size     = 256
  source_code_hash = data.archive_file.authorizer_zip.output_base64sha256

  environment {
    variables = {
      AUTHORIZED_USERS_TABLE = aws_dynamodb_table.authorized_users.name
      USAGE_TRACKING_TABLE   = aws_dynamodb_table.usage_tracking.name
      MAX_DAILY_REQUESTS     = var.max_daily_requests_per_user
      MAX_MONTHLY_REQUESTS   = var.max_monthly_requests_per_user
      TESTING_MODE          = var.testing_mode ? "true" : "false"
    }
  }

  tags = merge(
    {
      Name    = "${var.project_name}-authorizer-${var.environment}"
      Purpose = "API Gateway custom authorizer"
    },
    var.additional_tags
  )
}

# ===== AUTHORIZATION LAMBDA CODE =====

data "archive_file" "authorizer_zip" {
  type        = "zip"
  output_path = "${path.module}/temp/authorizer.zip"
  
  source {
    content = <<-EOF
import json
import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
authorized_table = dynamodb.Table(os.environ['AUTHORIZED_USERS_TABLE'])
usage_table = dynamodb.Table(os.environ['USAGE_TRACKING_TABLE'])

def lambda_handler(event, context):
    """
    Custom authorizer for API Gateway
    Validates phone numbers and enforces rate limits
    """
    
    # Extract phone number from request
    phone_number = extract_phone_number(event)
    
    if not phone_number:
        return generate_policy('Deny', event['methodArn'], {'error': 'No phone number provided'})
    
    # Check if user is authorized
    try:
        response = authorized_table.get_item(Key={'phone_number': phone_number})
        
        if 'Item' not in response:
            return generate_policy('Deny', event['methodArn'], {'error': 'Unauthorized phone number'})
        
        user = response['Item']
        
        # Check if user is active
        if user.get('status') != 'active':
            return generate_policy('Deny', event['methodArn'], {'error': 'User account inactive'})
        
        # Check rate limits
        if not check_rate_limits(phone_number):
            return generate_policy('Deny', event['methodArn'], {'error': 'Rate limit exceeded'})
        
        # Record usage
        record_usage(phone_number)
        
        # Return success policy with user context
        return generate_policy('Allow', event['methodArn'], {
            'user_id': user.get('user_id'),
            'phone_number': phone_number,
            'user_type': user.get('user_type', 'standard')
        })
        
    except Exception as e:
        print(f"Authorization error: {str(e)}")
        return generate_policy('Deny', event['methodArn'], {'error': 'Authorization failed'})

def extract_phone_number(event):
    """Extract phone number from various event sources"""
    
    # From headers
    headers = event.get('headers', {})
    if 'x-phone-number' in headers:
        return headers['x-phone-number']
    
    # From query parameters
    query_params = event.get('queryStringParameters') or {}
    if 'phone' in query_params:
        return query_params['phone']
    
    # From path parameters
    path_params = event.get('pathParameters') or {}
    if 'phone' in path_params:
        return path_params['phone']
    
    # From request body (for POST requests)
    if event.get('body'):
        try:
            body = json.loads(event['body'])
            if 'phone_number' in body:
                return body['phone_number']
        except:
            pass
    
    return None

def check_rate_limits(phone_number):
    """Check if user has exceeded rate limits"""
    
    today = datetime.now().strftime('%Y-%m-%d')
    month = datetime.now().strftime('%Y-%m')
    
    try:
        # Check daily usage
        daily_response = usage_table.get_item(
            Key={'phone_number': phone_number, 'date': today}
        )
        
        daily_count = 0
        if 'Item' in daily_response:
            daily_count = int(daily_response['Item'].get('request_count', 0))
        
        max_daily = int(os.environ.get('MAX_DAILY_REQUESTS', 50))
        if daily_count >= max_daily:
            return False
        
        # Check monthly usage
        monthly_response = usage_table.query(
            IndexName='MonthlyUsageIndex',
            KeyConditionExpression='month = :month AND phone_number = :phone',
            ExpressionAttributeValues={
                ':month': month,
                ':phone': phone_number
            }
        )
        
        monthly_count = sum(int(item.get('request_count', 0)) for item in monthly_response['Items'])
        max_monthly = int(os.environ.get('MAX_MONTHLY_REQUESTS', 1000))
        
        if monthly_count >= max_monthly:
            return False
        
        return True
        
    except Exception as e:
        print(f"Rate limit check error: {str(e)}")
        return False

def record_usage(phone_number):
    """Record API usage for rate limiting"""
    
    today = datetime.now().strftime('%Y-%m-%d')
    month = datetime.now().strftime('%Y-%m')
    timestamp = datetime.now().isoformat()
    
    try:
        # Update daily usage
        usage_table.update_item(
            Key={'phone_number': phone_number, 'date': today},
            UpdateExpression='SET request_count = if_not_exists(request_count, :zero) + :inc, '
                           'last_request = :timestamp, '
                           'month = :month, '
                           'expires_at = :expires',
            ExpressionAttributeValues={
                ':zero': 0,
                ':inc': 1,
                ':timestamp': timestamp,
                ':month': month,
                ':expires': int((datetime.now() + timedelta(days=90)).timestamp())
            }
        )
        
    except Exception as e:
        print(f"Usage recording error: {str(e)}")

def generate_policy(effect, resource, context=None):
    """Generate IAM policy for API Gateway"""
    
    policy = {
        'principalId': context.get('phone_number', 'unknown') if context else 'unknown',
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': resource
                }
            ]
        }
    }
    
    if context:
        policy['context'] = context
    
    return policy
EOF
    filename = "authorization.py"
  }
}

# ===== IAM ROLE FOR AUTHORIZER =====

resource "aws_iam_role" "authorizer_role" {
  name = "${var.project_name}-authorizer-role-${var.environment}"

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
      Name    = "${var.project_name}-authorizer-role-${var.environment}"
      Purpose = "IAM role for API Gateway authorizer"
    },
    var.additional_tags
  )
}

resource "aws_iam_role_policy_attachment" "authorizer_basic" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.authorizer_role.name
}

resource "aws_iam_role_policy" "authorizer_dynamodb" {
  name = "${var.project_name}-authorizer-dynamodb-${var.environment}"
  role = aws_iam_role.authorizer_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.authorized_users.arn,
          "${aws_dynamodb_table.authorized_users.arn}/index/*",
          aws_dynamodb_table.usage_tracking.arn,
          "${aws_dynamodb_table.usage_tracking.arn}/index/*"
        ]
      }
    ]
  })
}

# ===== WAF WEB ACL FOR ADDITIONAL PROTECTION =====

resource "aws_wafv2_web_acl" "api_protection" {
  count = var.enable_waf_protection ? 1 : 0
  name  = "${var.project_name}-api-protection-${var.environment}"
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
      metric_name                = "RateLimitRule"
      sampled_requests_enabled   = true
    }

    action {
      block {}
    }
  }

  # Geographic restriction (if enabled)
  dynamic "rule" {
    for_each = var.allowed_countries != null ? [1] : []
    content {
      name     = "GeoRestrictionRule"
      priority = 2

      override_action {
        none {}
      }

      statement {
        geo_match_statement {
          country_codes = var.allowed_countries
        }
      }

      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = "GeoRestrictionRule"
        sampled_requests_enabled   = true
      }

      action {
        allow {}
      }
    }
  }

  tags = merge(
    {
      Name    = "${var.project_name}-api-protection-${var.environment}"
      Purpose = "WAF protection for API Gateway"
    },
    var.additional_tags
  )

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.project_name}-api-protection-${var.environment}"
    sampled_requests_enabled   = true
  }
}

# ===== OUTPUTS =====

output "access_control_summary" {
  description = "Summary of access control measures"
  value = {
    authorized_users_table = aws_dynamodb_table.authorized_users.name
    usage_tracking_table   = aws_dynamodb_table.usage_tracking.name
    authorizer_function    = aws_lambda_function.authorizer.function_name
    max_daily_requests     = var.max_daily_requests_per_user
    max_monthly_requests   = var.max_monthly_requests_per_user
    waf_enabled           = var.enable_waf_protection
    testing_mode          = var.testing_mode
  }
}

output "authorization_config" {
  description = "Configuration for API Gateway authorization"
  value = {
    authorizer_arn         = aws_lambda_function.authorizer.arn
    authorizer_invoke_arn  = aws_lambda_function.authorizer.invoke_arn
    waf_acl_arn           = var.enable_waf_protection ? aws_wafv2_web_acl.api_protection[0].arn : null
  }
}
