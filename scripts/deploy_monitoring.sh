#!/bin/bash

# Comprehensive Monitoring Deployment Script
# This script deploys the complete monitoring infrastructure

set -e

echo "🚀 Starting AI Nutritionist Comprehensive Monitoring Deployment"

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
ENVIRONMENT="${ENVIRONMENT:-production}"
PROJECT_NAME="ai-nutritionist"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI not found. Please install AWS CLI first."
        exit 1
    fi
    
    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        print_error "Terraform not found. Please install Terraform first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found. Please install Python 3 first."
        exit 1
    fi
    
    print_success "All prerequisites checked"
}

create_s3_bucket() {
    print_status "Creating S3 bucket for Terraform state..."
    
    BUCKET_NAME="${PROJECT_NAME}-terraform-state-${ENVIRONMENT}"
    
    # Check if bucket exists
    if aws s3 ls "s3://${BUCKET_NAME}" 2>&1 | grep -q 'NoSuchBucket'; then
        # Create bucket
        if [ "$AWS_REGION" = "us-east-1" ]; then
            aws s3 mb "s3://${BUCKET_NAME}"
        else
            aws s3 mb "s3://${BUCKET_NAME}" --region "$AWS_REGION"
        fi
        
        # Enable versioning
        aws s3api put-bucket-versioning \
            --bucket "${BUCKET_NAME}" \
            --versioning-configuration Status=Enabled
        
        print_success "Created S3 bucket: ${BUCKET_NAME}"
    else
        print_status "S3 bucket already exists: ${BUCKET_NAME}"
    fi
}

create_dynamodb_tables() {
    print_status "Creating DynamoDB tables for monitoring..."
    
    # Monitoring Metrics Table
    aws dynamodb create-table \
        --table-name "${PROJECT_NAME}-monitoring-metrics" \
        --attribute-definitions \
            AttributeName=metric_id,AttributeType=S \
            AttributeName=timestamp,AttributeType=S \
        --key-schema \
            AttributeName=metric_id,KeyType=HASH \
            AttributeName=timestamp,KeyType=RANGE \
        --billing-mode PAY_PER_REQUEST \
        --region "$AWS_REGION" \
        --no-cli-pager 2>/dev/null || print_warning "Metrics table may already exist"
    
    # Incidents Table
    aws dynamodb create-table \
        --table-name "${PROJECT_NAME}-incidents" \
        --attribute-definitions \
            AttributeName=incident_id,AttributeType=S \
        --key-schema \
            AttributeName=incident_id,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --region "$AWS_REGION" \
        --no-cli-pager 2>/dev/null || print_warning "Incidents table may already exist"
    
    # Alerts Table
    aws dynamodb create-table \
        --table-name "${PROJECT_NAME}-monitoring-alerts" \
        --attribute-definitions \
            AttributeName=alert_id,AttributeType=S \
        --key-schema \
            AttributeName=alert_id,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --region "$AWS_REGION" \
        --no-cli-pager 2>/dev/null || print_warning "Alerts table may already exist"
    
    # Post-mortems Table
    aws dynamodb create-table \
        --table-name "${PROJECT_NAME}-postmortems" \
        --attribute-definitions \
            AttributeName=postmortem_id,AttributeType=S \
        --key-schema \
            AttributeName=postmortem_id,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --region "$AWS_REGION" \
        --no-cli-pager 2>/dev/null || print_warning "Post-mortems table may already exist"
    
    # Action Items Table
    aws dynamodb create-table \
        --table-name "${PROJECT_NAME}-action-items" \
        --attribute-definitions \
            AttributeName=action_item_id,AttributeType=S \
        --key-schema \
            AttributeName=action_item_id,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --region "$AWS_REGION" \
        --no-cli-pager 2>/dev/null || print_warning "Action items table may already exist"
    
    # Escalations Table
    aws dynamodb create-table \
        --table-name "${PROJECT_NAME}-escalations" \
        --attribute-definitions \
            AttributeName=escalation_id,AttributeType=S \
        --key-schema \
            AttributeName=escalation_id,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --region "$AWS_REGION" \
        --no-cli-pager 2>/dev/null || print_warning "Escalations table may already exist"
    
    print_success "DynamoDB tables created/verified"
}

package_lambda_functions() {
    print_status "Packaging Lambda functions..."
    
    # Create deployment directory
    mkdir -p deployment/lambda
    
    # Package comprehensive monitoring Lambda
    cd src/services/monitoring
    zip -r ../../../deployment/lambda/comprehensive_monitoring.zip \
        comprehensive_monitoring.py \
        config.py \
        requirements.txt
    
    # Package incident response Lambda
    zip -r ../../../deployment/lambda/incident_response.zip \
        incident_response.py \
        config.py \
        requirements.txt
    
    # Package post-mortem Lambda
    zip -r ../../../deployment/lambda/postmortem_automation.zip \
        postmortem_automation.py \
        config.py \
        requirements.txt
    
    cd ../../..
    
    print_success "Lambda functions packaged"
}

deploy_terraform() {
    print_status "Deploying Terraform infrastructure..."
    
    cd infrastructure/monitoring
    
    # Initialize Terraform
    terraform init \
        -backend-config="bucket=${PROJECT_NAME}-terraform-state-${ENVIRONMENT}" \
        -backend-config="key=monitoring/terraform.tfstate" \
        -backend-config="region=${AWS_REGION}"
    
    # Plan deployment
    print_status "Planning Terraform deployment..."
    terraform plan \
        -var="environment=${ENVIRONMENT}" \
        -var="aws_region=${AWS_REGION}" \
        -out=tfplan
    
    # Apply deployment
    print_status "Applying Terraform deployment..."
    terraform apply tfplan
    
    cd ../..
    
    print_success "Terraform infrastructure deployed"
}

create_lambda_functions() {
    print_status "Creating Lambda functions..."
    
    # Get account ID
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    
    # IAM role for Lambda functions
    ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${PROJECT_NAME}-monitoring-lambda-role"
    
    # Create IAM role if it doesn't exist
    aws iam create-role \
        --role-name "${PROJECT_NAME}-monitoring-lambda-role" \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }' 2>/dev/null || print_warning "IAM role may already exist"
    
    # Attach policies
    aws iam attach-role-policy \
        --role-name "${PROJECT_NAME}-monitoring-lambda-role" \
        --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    
    aws iam attach-role-policy \
        --role-name "${PROJECT_NAME}-monitoring-lambda-role" \
        --policy-arn "arn:aws:iam::aws:policy/CloudWatchFullAccess"
    
    aws iam attach-role-policy \
        --role-name "${PROJECT_NAME}-monitoring-lambda-role" \
        --policy-arn "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
    
    # Wait for role propagation
    sleep 10
    
    # Create comprehensive monitoring Lambda
    aws lambda create-function \
        --function-name "${PROJECT_NAME}-comprehensive-monitoring" \
        --runtime python3.9 \
        --role "$ROLE_ARN" \
        --handler comprehensive_monitoring.lambda_handler \
        --zip-file fileb://deployment/lambda/comprehensive_monitoring.zip \
        --timeout 300 \
        --memory-size 512 \
        --region "$AWS_REGION" 2>/dev/null || \
    aws lambda update-function-code \
        --function-name "${PROJECT_NAME}-comprehensive-monitoring" \
        --zip-file fileb://deployment/lambda/comprehensive_monitoring.zip \
        --region "$AWS_REGION"
    
    # Create incident response Lambda
    aws lambda create-function \
        --function-name "${PROJECT_NAME}-incident-response" \
        --runtime python3.9 \
        --role "$ROLE_ARN" \
        --handler incident_response.incident_handler \
        --zip-file fileb://deployment/lambda/incident_response.zip \
        --timeout 300 \
        --memory-size 512 \
        --region "$AWS_REGION" 2>/dev/null || \
    aws lambda update-function-code \
        --function-name "${PROJECT_NAME}-incident-response" \
        --zip-file fileb://deployment/lambda/incident_response.zip \
        --region "$AWS_REGION"
    
    # Create post-mortem Lambda
    aws lambda create-function \
        --function-name "${PROJECT_NAME}-postmortem-automation" \
        --runtime python3.9 \
        --role "$ROLE_ARN" \
        --handler postmortem_automation.postmortem_handler \
        --zip-file fileb://deployment/lambda/postmortem_automation.zip \
        --timeout 300 \
        --memory-size 512 \
        --region "$AWS_REGION" 2>/dev/null || \
    aws lambda update-function-code \
        --function-name "${PROJECT_NAME}-postmortem-automation" \
        --zip-file fileb://deployment/lambda/postmortem_automation.zip \
        --region "$AWS_REGION"
    
    print_success "Lambda functions created/updated"
}

setup_schedules() {
    print_status "Setting up CloudWatch Events schedules..."
    
    # Create rule for comprehensive monitoring (every 5 minutes)
    aws events put-rule \
        --name "${PROJECT_NAME}-monitoring-schedule" \
        --schedule-expression "rate(5 minutes)" \
        --description "Trigger comprehensive monitoring every 5 minutes" \
        --region "$AWS_REGION"
    
    # Add Lambda target
    aws events put-targets \
        --rule "${PROJECT_NAME}-monitoring-schedule" \
        --targets "Id"="1","Arn"="arn:aws:lambda:${AWS_REGION}:$(aws sts get-caller-identity --query Account --output text):function:${PROJECT_NAME}-comprehensive-monitoring" \
        --region "$AWS_REGION"
    
    # Add permission for EventBridge to invoke Lambda
    aws lambda add-permission \
        --function-name "${PROJECT_NAME}-comprehensive-monitoring" \
        --statement-id "allow-eventbridge" \
        --action "lambda:InvokeFunction" \
        --principal "events.amazonaws.com" \
        --source-arn "arn:aws:events:${AWS_REGION}:$(aws sts get-caller-identity --query Account --output text):rule/${PROJECT_NAME}-monitoring-schedule" \
        --region "$AWS_REGION" 2>/dev/null || print_warning "Permission may already exist"
    
    print_success "CloudWatch Events schedules configured"
}

create_sns_topics() {
    print_status "Creating SNS topics for alerts..."
    
    # Technical alerts topic
    aws sns create-topic \
        --name "${PROJECT_NAME}-alerts" \
        --region "$AWS_REGION"
    
    # Business alerts topic
    aws sns create-topic \
        --name "${PROJECT_NAME}-business-alerts" \
        --region "$AWS_REGION"
    
    # PagerDuty alerts topic
    aws sns create-topic \
        --name "${PROJECT_NAME}-pagerduty-alerts" \
        --region "$AWS_REGION"
    
    # Post-mortem review topic
    aws sns create-topic \
        --name "${PROJECT_NAME}-postmortem-reviews" \
        --region "$AWS_REGION"
    
    # Action item reminders topic
    aws sns create-topic \
        --name "${PROJECT_NAME}-action-item-reminders" \
        --region "$AWS_REGION"
    
    print_success "SNS topics created"
}

setup_cloudwatch_insights() {
    print_status "Setting up CloudWatch Insights queries..."
    
    # Error analysis query
    aws logs put-query-definition \
        --name "AI-Nutritionist-Error-Analysis" \
        --query-string 'fields @timestamp, @message, level, error, stack_trace | filter level = "ERROR" | sort @timestamp desc | limit 100' \
        --log-group-names "/ai-nutritionist/application" \
        --region "$AWS_REGION"
    
    # Performance analysis query
    aws logs put-query-definition \
        --name "AI-Nutritionist-Performance-Analysis" \
        --query-string 'fields @timestamp, operation, response_time, cache_hit, cost | filter response_time > 3000 | stats avg(response_time), max(response_time), count() by operation | sort avg(response_time) desc' \
        --log-group-names "/ai-nutritionist/performance" \
        --region "$AWS_REGION"
    
    # Business metrics query
    aws logs put-query-definition \
        --name "AI-Nutritionist-Business-Metrics" \
        --query-string 'fields @timestamp, event, user_id, amount, subscription_tier | filter event in ["SUBSCRIPTION_EVENT", "MEAL_PLAN_GENERATED", "USER_REGISTERED"] | stats count() by event, bin(5m) | sort @timestamp desc' \
        --log-group-names "/ai-nutritionist/application" \
        --region "$AWS_REGION"
    
    print_success "CloudWatch Insights queries configured"
}

validate_deployment() {
    print_status "Validating deployment..."
    
    # Check Lambda functions
    if aws lambda get-function --function-name "${PROJECT_NAME}-comprehensive-monitoring" --region "$AWS_REGION" >/dev/null 2>&1; then
        print_success "Comprehensive monitoring Lambda function deployed"
    else
        print_error "Comprehensive monitoring Lambda function not found"
    fi
    
    if aws lambda get-function --function-name "${PROJECT_NAME}-incident-response" --region "$AWS_REGION" >/dev/null 2>&1; then
        print_success "Incident response Lambda function deployed"
    else
        print_error "Incident response Lambda function not found"
    fi
    
    if aws lambda get-function --function-name "${PROJECT_NAME}-postmortem-automation" --region "$AWS_REGION" >/dev/null 2>&1; then
        print_success "Post-mortem automation Lambda function deployed"
    else
        print_error "Post-mortem automation Lambda function not found"
    fi
    
    # Test monitoring function
    print_status "Testing monitoring function..."
    aws lambda invoke \
        --function-name "${PROJECT_NAME}-comprehensive-monitoring" \
        --payload '{}' \
        --region "$AWS_REGION" \
        test_output.json
    
    if [ $? -eq 0 ]; then
        print_success "Monitoring function test successful"
        cat test_output.json
        rm test_output.json
    else
        print_error "Monitoring function test failed"
    fi
}

cleanup() {
    print_status "Cleaning up temporary files..."
    rm -rf deployment/
    print_success "Cleanup completed"
}

# Main deployment process
main() {
    echo "========================================"
    echo "AI Nutritionist Monitoring Deployment"
    echo "========================================"
    echo "Environment: $ENVIRONMENT"
    echo "AWS Region: $AWS_REGION"
    echo "Project: $PROJECT_NAME"
    echo "========================================"
    
    check_prerequisites
    create_s3_bucket
    create_dynamodb_tables
    package_lambda_functions
    create_lambda_functions
    setup_schedules
    create_sns_topics
    setup_cloudwatch_insights
    validate_deployment
    cleanup
    
    print_success "🎉 Comprehensive monitoring deployment completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Configure PagerDuty integration keys in the Lambda environment variables"
    echo "2. Subscribe email addresses to SNS topics"
    echo "3. Set up Slack webhook URLs"
    echo "4. Review and customize alert thresholds in config.py"
    echo "5. Test the monitoring system with sample alerts"
    echo ""
    echo "Dashboard URLs:"
    echo "• CloudWatch: https://console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#dashboards:"
    echo "• Lambda Functions: https://console.aws.amazon.com/lambda/home?region=${AWS_REGION}#/functions"
    echo "• DynamoDB Tables: https://console.aws.amazon.com/dynamodb/home?region=${AWS_REGION}#tables:"
}

# Run deployment
main "$@"
