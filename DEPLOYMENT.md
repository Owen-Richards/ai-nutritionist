# Deployment Guide

This guide covers deploying the AI Nutritionist Assistant to AWS using AWS SAM.

## Prerequisites

- AWS CLI configured with appropriate permissions
- AWS SAM CLI installed
- Python 3.11+
- Twilio account with WhatsApp API access

## Deployment Steps

### 1. Prepare Environment

```bash
# Clone repository
git clone <repository-url>
cd ai-nutritionalist

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure AWS Parameters

Set up required parameters in AWS Systems Manager Parameter Store:

```bash
# Twilio configuration
aws ssm put-parameter --name "/ai-nutritionist/twilio/account-sid" --value "your-twilio-sid" --type "String"
aws ssm put-parameter --name "/ai-nutritionist/twilio/auth-token" --value "your-twilio-token" --type "SecureString"
aws ssm put-parameter --name "/ai-nutritionist/twilio/phone-number" --value "your-phone-number" --type "String"
```

### 3. Deploy Infrastructure

```bash
cd infrastructure

# Build the application
sam build

# Deploy (first time - guided)
sam deploy --guided

# Subsequent deployments
sam deploy
```

### 4. Configure Twilio Webhook

After deployment, update your Twilio webhook URL:

1. Get API Gateway URL from SAM output
2. In Twilio Console, set webhook URL to: `https://your-api-url/webhook`

### 5. Test Deployment

Send a test message to your Twilio WhatsApp number:
```
"Hello"
```

You should receive a welcome message from the AI Nutritionist.

## Environment-Specific Deployments

### Development
```bash
sam deploy --parameter-overrides Environment=dev
```

### Staging
```bash
sam deploy --parameter-overrides Environment=staging
```

### Production
```bash
sam deploy --parameter-overrides Environment=prod
```

## Monitoring

After deployment, monitor:
- CloudWatch Logs for Lambda functions
- CloudWatch Metrics for performance
- AWS Bedrock usage and costs
- DynamoDB usage

## Rollback

If issues occur:
```bash
# Rollback to previous version
sam deploy --parameter-overrides Environment=prod --rollback

# Or delete and redeploy
sam delete
sam deploy --guided
```
