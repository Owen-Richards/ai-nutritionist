# Setup & Deployment Guide

## Prerequisites

Before setting up the AI Nutritionist Assistant, ensure you have:

### Required Software
- **Python 3.11+** ([Download](https://www.python.org/downloads/))
- **AWS CLI** configured with appropriate permissions ([Installation Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html))
- **AWS SAM CLI** ([Installation Guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html))
- **Docker** for local testing ([Download](https://www.docker.com/products/docker-desktop/))
- **Git** for version control

### AWS Account Requirements
- AWS account with administrator access
- Billing alerts configured
- Service quotas sufficient for Lambda, DynamoDB, and API Gateway

### External Services
- **Twilio account** with WhatsApp Business API access ([Sign up](https://www.twilio.com/try-twilio))
- **Edamam API accounts** for recipe and nutrition data ([Sign up](https://developer.edamam.com/))

## Development Setup

### 1. Clone Repository
```bash
git clone https://github.com/Owen-Richards/ai-nutritionist.git
cd ai-nutritionist
```

### 2. Python Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development tools
```

### 3. Configure Environment Variables

Create `.env` file for local development:
```bash
# Twilio Configuration
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# Edamam API Keys
EDAMAM_RECIPE_API_KEY=your_recipe_key
EDAMAM_RECIPE_APP_ID=your_recipe_app_id
EDAMAM_NUTRITION_API_KEY=your_nutrition_key
EDAMAM_NUTRITION_APP_ID=your_nutrition_app_id

# AWS Configuration (for local testing)
AWS_REGION=us-east-1
AWS_PROFILE=default
```

### 4. Install Pre-commit Hooks
```bash
pre-commit install
```

### 5. Validate Setup
```bash
# Run tests
python -m pytest tests/ -v

# Check code formatting
python -m black src/ tests/ --check

# Run linting
python -m flake8 src/ tests/
```

## AWS Configuration

### 1. Configure AWS CLI
```bash
aws configure
# Enter your AWS Access Key ID, Secret Access Key, and region
```

### 2. Set Up Parameter Store
Store sensitive configuration in AWS Systems Manager Parameter Store:

```bash
# Twilio Configuration
aws ssm put-parameter \
  --name "/ai-nutritionist/twilio/account-sid" \
  --value "your-twilio-account-sid" \
  --type "String"

aws ssm put-parameter \
  --name "/ai-nutritionist/twilio/auth-token" \
  --value "your-twilio-auth-token" \
  --type "SecureString"

aws ssm put-parameter \
  --name "/ai-nutritionist/twilio/phone-number" \
  --value "+1234567890" \
  --type "String"

# Edamam API Configuration
aws ssm put-parameter \
  --name "/ai-nutritionist/edamam/recipe-api-key" \
  --value "your-recipe-api-key" \
  --type "SecureString"

aws ssm put-parameter \
  --name "/ai-nutritionist/edamam/nutrition-api-key" \
  --value "your-nutrition-api-key" \
  --type "SecureString"
```

### 3. Configure DynamoDB Tables
Tables are automatically created during deployment, but you can pre-create them:

```bash
# User preferences table
aws dynamodb create-table \
  --table-name ai-nutritionist-users \
  --attribute-definitions \
    AttributeName=user_id,AttributeType=S \
  --key-schema \
    AttributeName=user_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# Meal plans table
aws dynamodb create-table \
  --table-name ai-nutritionist-meal-plans \
  --attribute-definitions \
    AttributeName=user_id,AttributeType=S \
    AttributeName=created_at,AttributeType=S \
  --key-schema \
    AttributeName=user_id,KeyType=HASH \
    AttributeName=created_at,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST
```

## Local Development

### 1. Start Local API Gateway
```bash
sam build
sam local start-api --port 3000
```

### 2. Test Webhook Endpoints
```bash
# Test WhatsApp webhook
curl -X POST http://localhost:3000/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "From": "+1234567890",
    "Body": "I want a meal plan for this week",
    "MessageSid": "test123"
  }'
```

### 3. Run Local DynamoDB (Optional)
```bash
# Download and run DynamoDB Local
docker run -p 8000:8000 amazon/dynamodb-local

# Create local tables
aws dynamodb create-table \
  --table-name ai-nutritionist-users \
  --attribute-definitions AttributeName=user_id,AttributeType=S \
  --key-schema AttributeName=user_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --endpoint-url http://localhost:8000
```

## Production Deployment

### 1. Build Application
```bash
sam build --use-container
```

### 2. Deploy Infrastructure
```bash
# First-time deployment with guided setup
sam deploy --guided

# Follow prompts to configure:
# - Stack name: ai-nutritionist-prod
# - AWS Region: us-east-1
# - Parameter overrides: Environment=production
# - Save parameters: Y
```

### 3. Configure Custom Domain (Optional)
```bash
# Create ACM certificate
aws acm request-certificate \
  --domain-name api.yourdomain.com \
  --validation-method DNS

# Update SAM template with custom domain configuration
# Then redeploy
sam deploy
```

### 4. Set Up Monitoring
```bash
# Create CloudWatch dashboard
aws cloudwatch put-dashboard \
  --dashboard-name "AI-Nutritionist-Dashboard" \
  --dashboard-body file://monitoring/dashboard.json

# Set up cost alerts
aws budgets create-budget \
  --account-id YOUR_ACCOUNT_ID \
  --budget file://monitoring/budget.json
```

## Environment Configuration

### Development Environment
```yaml
# samconfig.toml
[default.deploy.parameters]
stack_name = "ai-nutritionist-dev"
s3_bucket = "ai-nutritionist-dev-deployments"
region = "us-east-1"
parameter_overrides = "Environment=development DebugMode=true"
```

### Production Environment
```yaml
# samconfig.toml
[production.deploy.parameters]
stack_name = "ai-nutritionist-prod"
s3_bucket = "ai-nutritionist-prod-deployments"
region = "us-east-1"
parameter_overrides = "Environment=production DebugMode=false"
```

## Twilio WhatsApp Setup

### 1. WhatsApp Business API
1. Apply for WhatsApp Business API access through Twilio
2. Complete business verification process
3. Configure webhook URL: `https://your-api-gateway-url/webhook/whatsapp`

### 2. Phone Number Configuration
```bash
# Configure webhook for your Twilio phone number
curl -X POST https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID/IncomingPhoneNumbers/$PHONE_NUMBER_SID.json \
  --data-urlencode "SmsUrl=https://your-api-gateway-url/webhook/whatsapp" \
  --data-urlencode "SmsMethod=POST" \
  -u $TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN
```

### 3. Test WhatsApp Integration
1. Send a test message to your Twilio WhatsApp number
2. Check CloudWatch logs for successful processing
3. Verify response is received in WhatsApp

## International Deployment

### Multi-Region Setup
```bash
# Deploy to multiple regions
sam deploy --region us-east-1 --config-env us-east-1
sam deploy --region eu-west-1 --config-env eu-west-1
sam deploy --region ap-southeast-1 --config-env ap-southeast-1
```

### Phone Number Configuration
```bash
# Configure international phone numbers
aws ssm put-parameter \
  --name "/ai-nutritionist/twilio/phone-number-us" \
  --value "+1234567890" \
  --type "String"

aws ssm put-parameter \
  --name "/ai-nutritionist/twilio/phone-number-uk" \
  --value "+44123456789" \
  --type "String"
```

## Database Migration

### Initial Schema Setup
```bash
# Run database migrations
python scripts/setup_database.py

# Create indexes for performance
aws dynamodb update-table \
  --table-name ai-nutritionist-users \
  --global-secondary-indexes file://database/gsi-config.json
```

### Data Backup
```bash
# Enable point-in-time recovery
aws dynamodb update-continuous-backups \
  --table-name ai-nutritionist-users \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true

# Create on-demand backup
aws dynamodb create-backup \
  --table-name ai-nutritionist-users \
  --backup-name "ai-nutritionist-users-$(date +%Y%m%d)"
```

## Security Configuration

### IAM Roles and Policies
```bash
# Create execution role for Lambda functions
aws iam create-role \
  --role-name ai-nutritionist-lambda-role \
  --assume-role-policy-document file://iam/lambda-trust-policy.json

# Attach policies
aws iam attach-role-policy \
  --role-name ai-nutritionist-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

### API Gateway Security
```bash
# Enable AWS WAF
aws wafv2 create-web-acl \
  --name ai-nutritionist-waf \
  --scope REGIONAL \
  --default-action Allow={} \
  --rules file://security/waf-rules.json
```

## Monitoring and Observability

### CloudWatch Setup
```bash
# Create log groups
aws logs create-log-group --log-group-name /aws/lambda/ai-nutritionist-webhook
aws logs create-log-group --log-group-name /aws/lambda/ai-nutritionist-meal-generator

# Set retention policy
aws logs put-retention-policy \
  --log-group-name /aws/lambda/ai-nutritionist-webhook \
  --retention-in-days 30
```

### Cost Monitoring
```bash
# Set up billing alerts
aws cloudwatch put-metric-alarm \
  --alarm-name "AI-Nutritionist-Cost-Alert" \
  --alarm-description "Alert when monthly costs exceed $100" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --threshold 100 \
  --comparison-operator GreaterThanThreshold
```

## Troubleshooting

### Common Issues

#### Lambda Cold Starts
```bash
# Enable provisioned concurrency for critical functions
aws lambda put-provisioned-concurrency-config \
  --function-name ai-nutritionist-webhook \
  --qualifier $LATEST \
  --provisioned-concurrency-capacity 5
```

#### DynamoDB Throttling
```bash
# Increase read/write capacity
aws dynamodb update-table \
  --table-name ai-nutritionist-users \
  --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=10
```

#### API Gateway Timeouts
```bash
# Check CloudWatch logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/ai-nutritionist-webhook \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "ERROR"
```

### Performance Optimization

#### Lambda Memory Optimization
```bash
# Test different memory configurations
aws lambda update-function-configuration \
  --function-name ai-nutritionist-meal-generator \
  --memory-size 1024

# Monitor execution duration and costs
```

#### DynamoDB Performance
```bash
# Enable auto-scaling
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/ai-nutritionist-users \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --min-capacity 5 \
  --max-capacity 100
```

## Rollback Procedures

### Application Rollback
```bash
# Rollback to previous deployment
sam deploy --parameter-overrides Version=previous

# Or use AWS CLI to update Lambda function
aws lambda update-function-code \
  --function-name ai-nutritionist-webhook \
  --zip-file fileb://previous-deployment.zip
```

### Database Rollback
```bash
# Restore from point-in-time backup
aws dynamodb restore-table-from-backup \
  --target-table-name ai-nutritionist-users-restored \
  --backup-arn arn:aws:dynamodb:region:account:table/ai-nutritionist-users/backup/backup-id
```

## Maintenance

### Regular Updates
```bash
# Update dependencies
pip install --upgrade -r requirements.txt

# Update SAM CLI
pip install --upgrade aws-sam-cli

# Update AWS CLI
pip install --upgrade awscli
```

### Health Checks
```bash
# Automated health check script
#!/bin/bash
curl -f https://your-api-gateway-url/health || exit 1
aws dynamodb describe-table --table-name ai-nutritionist-users || exit 1
```

## Support

For deployment issues:
- Check [GitHub Issues](https://github.com/Owen-Richards/ai-nutritionist/issues)
- Review CloudWatch logs
- Contact support at support@ai-nutritionist.com
