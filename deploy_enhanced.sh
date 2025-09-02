#!/bin/bash

# Enhanced deployment script for AI Nutritionist with Edamam integration
# This script sets up all necessary AWS resources and configurations

set -e

# Configuration
STACK_NAME="ai-nutritionist"
ENVIRONMENT="dev"
AWS_REGION="us-east-1"

echo "🚀 Deploying AI Nutritionist with Enhanced Edamam Integration..."

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

# Check if SAM CLI is installed
if ! command -v sam &> /dev/null; then
    echo "❌ AWS SAM CLI not found. Please install it first."
    echo "Visit: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html"
    exit 1
fi

# Prompt for Edamam API credentials
echo "📝 Setting up Edamam API credentials..."

if [ -z "$EDAMAM_RECIPE_APP_ID" ]; then
    read -p "Enter your Edamam Recipe Search App ID: " EDAMAM_RECIPE_APP_ID
fi

if [ -z "$EDAMAM_RECIPE_API_KEY" ]; then
    read -s -p "Enter your Edamam Recipe Search API Key: " EDAMAM_RECIPE_API_KEY
    echo
fi

if [ -z "$EDAMAM_NUTRITION_APP_ID" ]; then
    read -p "Enter your Edamam Nutrition Analysis App ID: " EDAMAM_NUTRITION_APP_ID
fi

if [ -z "$EDAMAM_NUTRITION_API_KEY" ]; then
    read -s -p "Enter your Edamam Nutrition Analysis API Key: " EDAMAM_NUTRITION_API_KEY
    echo
fi

if [ -z "$EDAMAM_FOOD_DB_APP_ID" ]; then
    read -p "Enter your Edamam Food Database App ID: " EDAMAM_FOOD_DB_APP_ID
fi

if [ -z "$EDAMAM_FOOD_DB_API_KEY" ]; then
    read -s -p "Enter your Edamam Food Database API Key: " EDAMAM_FOOD_DB_API_KEY
    echo
fi

# Prompt for messaging service credentials (optional)
echo "📱 Setting up messaging service credentials..."

if [ -z "$TWILIO_ACCOUNT_SID" ]; then
    read -p "Enter your Twilio Account SID (or press Enter to skip): " TWILIO_ACCOUNT_SID
fi

if [ -z "$TWILIO_AUTH_TOKEN" ] && [ ! -z "$TWILIO_ACCOUNT_SID" ]; then
    read -s -p "Enter your Twilio Auth Token: " TWILIO_AUTH_TOKEN
    echo
fi

# Store credentials in AWS Systems Manager Parameter Store
echo "🔐 Storing API credentials securely in AWS Parameter Store..."

# Edamam credentials
aws ssm put-parameter \
    --name "/ai-nutritionist/edamam/recipe-app-id" \
    --value "$EDAMAM_RECIPE_APP_ID" \
    --type "SecureString" \
    --overwrite \
    --region $AWS_REGION

aws ssm put-parameter \
    --name "/ai-nutritionist/edamam/recipe-api-key" \
    --value "$EDAMAM_RECIPE_API_KEY" \
    --type "SecureString" \
    --overwrite \
    --region $AWS_REGION

aws ssm put-parameter \
    --name "/ai-nutritionist/edamam/nutrition-app-id" \
    --value "$EDAMAM_NUTRITION_APP_ID" \
    --type "SecureString" \
    --overwrite \
    --region $AWS_REGION

aws ssm put-parameter \
    --name "/ai-nutritionist/edamam/nutrition-api-key" \
    --value "$EDAMAM_NUTRITION_API_KEY" \
    --type "SecureString" \
    --overwrite \
    --region $AWS_REGION

aws ssm put-parameter \
    --name "/ai-nutritionist/edamam/food-db-app-id" \
    --value "$EDAMAM_FOOD_DB_APP_ID" \
    --type "SecureString" \
    --overwrite \
    --region $AWS_REGION

aws ssm put-parameter \
    --name "/ai-nutritionist/edamam/food-db-api-key" \
    --value "$EDAMAM_FOOD_DB_API_KEY" \
    --type "SecureString" \
    --overwrite \
    --region $AWS_REGION

# Twilio credentials (if provided)
if [ ! -z "$TWILIO_ACCOUNT_SID" ]; then
    aws ssm put-parameter \
        --name "/ai-nutritionist/twilio/account-sid" \
        --value "$TWILIO_ACCOUNT_SID" \
        --type "SecureString" \
        --overwrite \
        --region $AWS_REGION

    aws ssm put-parameter \
        --name "/ai-nutritionist/twilio/auth-token" \
        --value "$TWILIO_AUTH_TOKEN" \
        --type "SecureString" \
        --overwrite \
        --region $AWS_REGION
fi

echo "✅ API credentials stored successfully!"

# Build the SAM application
echo "🏗️ Building SAM application..."
sam build

# Deploy the SAM application
echo "🚀 Deploying SAM application..."
sam deploy \
    --stack-name "${STACK_NAME}-${ENVIRONMENT}" \
    --parameter-overrides "Environment=${ENVIRONMENT}" \
    --capabilities CAPABILITY_IAM \
    --resolve-s3 \
    --region $AWS_REGION

# Get the API Gateway URL
API_GATEWAY_URL=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}-${ENVIRONMENT}" \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
    --output text \
    --region $AWS_REGION)

echo "✅ Deployment completed successfully!"
echo ""
echo "📊 **Deployment Summary**"
echo "========================"
echo "Stack Name: ${STACK_NAME}-${ENVIRONMENT}"
echo "Region: $AWS_REGION"
echo "API Gateway URL: $API_GATEWAY_URL"
echo ""
echo "🔗 **Webhook URLs for Messaging Platforms:**"
echo "WhatsApp: ${API_GATEWAY_URL}/whatsapp"
echo "SMS: ${API_GATEWAY_URL}/sms"
echo "Telegram: ${API_GATEWAY_URL}/telegram"
echo "Messenger: ${API_GATEWAY_URL}/messenger"
echo ""
echo "💡 **Next Steps:**"
echo "1. Configure your messaging platform webhooks with the URLs above"
echo "2. Test the integration by sending a message"
echo "3. Monitor costs in the AWS console"
echo "4. Check API usage in DynamoDB tables"
echo ""

# Optional: Run tests
read -p "🧪 Would you like to run the test suite? (y/n): " RUN_TESTS

if [ "$RUN_TESTS" = "y" ] || [ "$RUN_TESTS" = "Y" ]; then
    echo "🧪 Running test suite..."
    
    # Install test dependencies if not already installed
    pip install pytest pytest-asyncio
    
    # Run the Edamam integration tests
    python -m pytest tests/test_edamam_integration.py -v
    
    echo "✅ Tests completed!"
fi

# Display cost optimization tips
echo ""
echo "💰 **Cost Optimization Tips:**"
echo "================================"
echo "1. Edamam API costs are tracked in DynamoDB"
echo "2. Recipe searches are cached for 48 hours"
echo "3. Nutrition analyses are cached for 24 hours"
echo "4. Ingredient validations are cached for 7 days"
echo "5. Monitor usage with: aws dynamodb scan --table-name ai-nutritionist-api-usage-${ENVIRONMENT}"
echo ""
echo "📈 **Expected Monthly Costs (1000 active users):**"
echo "- Edamam APIs: ~\$30-50"
echo "- AWS Lambda: ~\$10-20"
echo "- DynamoDB: ~\$5-15"
echo "- API Gateway: ~\$3-10"
echo "Total: ~\$48-95/month"
echo ""

# Setup monitoring alerts (optional)
read -p "🔔 Would you like to set up cost monitoring alerts? (y/n): " SETUP_ALERTS

if [ "$SETUP_ALERTS" = "y" ] || [ "$SETUP_ALERTS" = "Y" ]; then
    echo "📊 Setting up CloudWatch alarms for cost monitoring..."
    
    # Create CloudWatch alarm for high API usage
    aws cloudwatch put-metric-alarm \
        --alarm-name "ai-nutritionist-high-api-usage" \
        --alarm-description "Alert when API usage is high" \
        --metric-name "ConsumedReadCapacityUnits" \
        --namespace "AWS/DynamoDB" \
        --statistic "Sum" \
        --period 3600 \
        --threshold 1000 \
        --comparison-operator "GreaterThanThreshold" \
        --dimensions Name=TableName,Value="ai-nutritionist-api-usage-${ENVIRONMENT}" \
        --evaluation-periods 1 \
        --region $AWS_REGION
    
    echo "✅ Monitoring alerts configured!"
fi

echo ""
echo "🎉 **Enhanced AI Nutritionist with Edamam Integration Deployed Successfully!**"
echo ""
echo "📚 **Documentation:**"
echo "- README.md: General project information"
echo "- DEPLOYMENT.md: Detailed deployment guide"
echo "- API_GUIDE.md: API usage and integration guide"
echo ""
echo "🔧 **Troubleshooting:**"
echo "- Check CloudWatch logs for Lambda function errors"
echo "- Verify API credentials in Parameter Store"
echo "- Monitor DynamoDB tables for usage patterns"
echo "- Test webhooks with curl or Postman"
echo ""
echo "Happy cooking! 🍽️✨"
