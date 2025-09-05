#!/bin/bash

# AI Nutritionist Production Deployment Script
# Deploys production-ready infrastructure with security hardening

set -e

echo "🚀 AI Nutritionist - Production Deployment"
echo "=========================================="

# Configuration
ENVIRONMENT="prod"
AWS_REGION="${AWS_REGION:-us-east-1}"
STACK_NAME="ai-nutritionist-prod"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Prerequisites check
print_status "Checking production deployment prerequisites..."

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI not found. Please install it first."
    exit 1
fi

# Check SAM CLI
if ! command -v sam &> /dev/null; then
    print_error "AWS SAM CLI not found. Please install it first."
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured or expired."
    print_status "Please run: aws configure"
    exit 1
fi

# Get account info
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region || echo "us-east-1")

print_success "AWS Account: $AWS_ACCOUNT_ID"
print_success "Region: $AWS_REGION"

# Production safety check
echo ""
print_warning "⚠️  PRODUCTION DEPLOYMENT WARNING ⚠️"
echo "This will deploy to PRODUCTION environment."
echo "Account: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"
echo "Stack: $STACK_NAME"
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    print_status "Deployment cancelled."
    exit 0
fi

# Set up production environment
print_status "Setting up production environment variables..."
export AWS_DEFAULT_REGION=$AWS_REGION

# Install dependencies
print_status "Installing Python dependencies..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate || source .venv/Scripts/activate
pip install -r requirements.txt

# Run production validation tests
print_status "Running production validation tests..."
python -m pytest tests/test_project_validation.py -v
if [ $? -ne 0 ]; then
    print_error "Validation tests failed. Aborting deployment."
    exit 1
fi

# Build SAM application
print_status "Building SAM application for production..."
cd infrastructure
sam build

# Deploy with production parameters
print_status "Deploying to production environment..."
sam deploy \
    --stack-name "$STACK_NAME" \
    --parameter-overrides \
        Environment=prod \
        LogLevel=INFO \
        EnableXRayTracing=true \
        EnableVPC=true \
        EnableWAF=true \
        EnableCloudFrontLogging=true \
        BackupRetentionDays=30 \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --resolve-s3 \
    --no-confirm-changeset \
    --region $AWS_REGION

# Get deployment outputs
print_status "Retrieving deployment outputs..."
API_GATEWAY_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
    --output text \
    --region $AWS_REGION 2>/dev/null || echo "Not available")

CLOUDFRONT_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontUrl`].OutputValue' \
    --output text \
    --region $AWS_REGION 2>/dev/null || echo "Not available")

cd ..

# Set up production secrets
print_status "Setting up production secrets (if not exists)..."

# Check and create parameters if they don't exist
check_and_create_param() {
    local param_name=$1
    local param_value=$2
    local param_type=$3
    
    if ! aws ssm get-parameter --name "$param_name" --region $AWS_REGION &>/dev/null; then
        print_warning "Parameter $param_name not found. Please set it manually:"
        echo "aws ssm put-parameter --name '$param_name' --value '$param_value' --type '$param_type' --region $AWS_REGION"
    else
        print_success "Parameter $param_name already exists"
    fi
}

echo ""
print_status "Checking required parameters..."
check_and_create_param "/ai-nutritionist/bedrock/model-id" "anthropic.claude-3-haiku-20240307-v1:0" "String"
check_and_create_param "/ai-nutritionist/edamam/app-id" "your-app-id" "String"
check_and_create_param "/ai-nutritionist/edamam/app-key" "your-app-key" "SecureString"
check_and_create_param "/ai-nutritionist/stripe/secret-key" "sk_live_your-secret-key" "SecureString"
check_and_create_param "/ai-nutritionist/stripe/webhook-secret" "whsec_your-webhook-secret" "SecureString"

# Set up CloudWatch alarms
print_status "Setting up CloudWatch monitoring..."

# API Gateway error alarm
aws cloudwatch put-metric-alarm \
    --alarm-name "ai-nutritionist-prod-api-errors" \
    --alarm-description "High error rate on API Gateway" \
    --metric-name "5XXError" \
    --namespace "AWS/ApiGateway" \
    --statistic "Sum" \
    --period 300 \
    --threshold 10 \
    --comparison-operator "GreaterThanThreshold" \
    --dimensions Name=ApiName,Value="ai-nutritionist-prod" \
    --evaluation-periods 2 \
    --region $AWS_REGION || true

# Lambda duration alarm  
aws cloudwatch put-metric-alarm \
    --alarm-name "ai-nutritionist-prod-lambda-duration" \
    --alarm-description "Lambda function taking too long" \
    --metric-name "Duration" \
    --namespace "AWS/Lambda" \
    --statistic "Average" \
    --period 300 \
    --threshold 25000 \
    --comparison-operator "GreaterThanThreshold" \
    --dimensions Name=FunctionName,Value="ai-nutritionist-message-handler-prod" \
    --evaluation-periods 2 \
    --region $AWS_REGION || true

# Cost alarm
aws cloudwatch put-metric-alarm \
    --alarm-name "ai-nutritionist-prod-cost-alarm" \
    --alarm-description "Monthly cost exceeding budget" \
    --metric-name "EstimatedCharges" \
    --namespace "AWS/Billing" \
    --statistic "Maximum" \
    --period 86400 \
    --threshold 500 \
    --comparison-operator "GreaterThanThreshold" \
    --dimensions Name=Currency,Value=USD \
    --evaluation-periods 1 \
    --region us-east-1 || true

print_success "CloudWatch alarms configured"

# Create production environment file
print_status "Creating production environment configuration..."
cat > .env.production << EOF
# AI Nutritionist - PRODUCTION Environment
# Generated on $(date)

# Environment
ENVIRONMENT=prod
AWS_DEFAULT_REGION=$AWS_REGION
LOG_LEVEL=INFO

# Deployment Info
STACK_NAME=$STACK_NAME
API_GATEWAY_URL=$API_GATEWAY_URL
CLOUDFRONT_URL=$CLOUDFRONT_URL

# Security
ENABLE_WAF=true
ENABLE_XRAY_TRACING=true
ENABLE_VPC=true

# Monitoring
ENABLE_DETAILED_MONITORING=true
ENABLE_COST_MONITORING=true

# Performance
LAMBDA_TIMEOUT=30
LAMBDA_MEMORY=512
CACHE_TTL=3600

# DynamoDB Tables
DYNAMODB_USER_TABLE=ai-nutritionist-users-prod
DYNAMODB_SUBSCRIPTIONS_TABLE=ai-nutritionist-subscriptions-prod
DYNAMODB_USAGE_TABLE=ai-nutritionist-usage-prod
DYNAMODB_REVENUE_TABLE=ai-nutritionist-revenue-prod
EOF

# Summary
echo ""
echo "🎉 PRODUCTION DEPLOYMENT COMPLETED!"
echo "=================================="
echo ""
print_success "Stack Name: $STACK_NAME"
print_success "Region: $AWS_REGION"
print_success "API Gateway URL: $API_GATEWAY_URL"
print_success "CloudFront URL: $CLOUDFRONT_URL"
echo ""

echo "📊 Production Features Enabled:"
echo "• WAF protection for API security"
echo "• VPC isolation for Lambda functions"
echo "• X-Ray tracing for performance monitoring"
echo "• CloudWatch alarms for proactive monitoring"
echo "• Enhanced backup and retention policies"
echo "• SSL/TLS encryption everywhere"
echo ""

echo "⚙️  Next Steps:"
echo "1. Configure messaging platform webhooks:"
echo "   - WhatsApp: Set webhook to $API_GATEWAY_URL/webhook"
echo "   - SMS: Set webhook to $API_GATEWAY_URL/sms/webhook"
echo ""
echo "2. Set up the required parameters (see warnings above)"
echo ""
echo "3. Test the production deployment:"
echo "   curl -X POST $API_GATEWAY_URL/webhook -d '{\"test\": true}'"
echo ""
echo "4. Monitor the CloudWatch dashboard"
echo ""

print_success "Production deployment ready! 🚀"
