# íº€ AI Nutritionist Deployment Guide

## Overview

This guide covers deploying the AI Nutritionist application to AWS using AWS SAM (Serverless Application Model).

## Prerequisites

Before deploying, ensure you have:

- **AWS CLI** installed and configured with appropriate credentials
- **AWS SAM CLI** installed
- **Docker** installed (required by SAM for building)
- **Python 3.11+** installed locally
- Valid AWS account with necessary permissions

## AWS Setup

### 1. Configure AWS Credentials

```bash
aws configure
# Enter your AWS Access Key ID, Secret Access Key, Region, and Output format
```

### 2. Verify AWS Configuration

```bash
aws sts get-caller-identity
# Should return your AWS account details
```

### 3. Set Environment Variables

```bash
export AWS_REGION=us-east-1
export AWS_DEFAULT_REGION=us-east-1
```

## Deployment Process

### 1. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install development dependencies (for testing)
pip install -r requirements-dev.txt
```

### 2. Run Tests (Recommended)

```bash
# Run all tests to ensure everything works
python -m pytest tests/ -v

# Run validation tests specifically
python -m pytest tests/test_project_validation.py -v
```

### 3. Build the Application

```bash
sam build
```

This command:
- Downloads dependencies for each Lambda function
- Builds the application according to `template.yaml`
- Creates a `.aws-sam` directory with build artifacts

### 4. Deploy the Application

#### First-time Deployment (Guided)

```bash
sam deploy --guided
```

You'll be prompted to configure:
- Stack name (e.g., `ai-nutritionist-prod`)
- AWS Region (e.g., `us-east-1`)
- Parameter values (API keys, etc.)
- IAM role creation confirmation
- Function timeout settings

#### Subsequent Deployments

```bash
sam deploy
```

Uses the configuration from `samconfig.toml` created during guided deployment.

### 5. Environment-Specific Deployments

#### Development Environment

```bash
sam deploy --config-env dev --guided
```

#### Production Environment

```bash
sam deploy --config-env prod --guided
```

## Configuration Management

### 1. SAM Configuration File

Edit `samconfig.toml` for environment-specific settings:

```toml
[default.deploy.parameters]
stack_name = "ai-nutritionist"
s3_bucket = "your-deployment-bucket"
region = "us-east-1"
confirm_changeset = true
capabilities = "CAPABILITY_IAM"

[dev.deploy.parameters]
stack_name = "ai-nutritionist-dev"
parameter_overrides = "Environment=dev"

[prod.deploy.parameters]
stack_name = "ai-nutritionist-prod"
parameter_overrides = "Environment=prod"
```

### 2. Environment Variables

Set these in AWS Systems Manager Parameter Store or Lambda environment variables:

```bash
# Required API Keys
EDAMAM_APP_ID=your_edamam_app_id
EDAMAM_APP_KEY=your_edamam_app_key
OPENAI_API_KEY=your_openai_api_key

# WhatsApp/Messaging
WHATSAPP_VERIFY_TOKEN=your_verify_token
WHATSAPP_ACCESS_TOKEN=your_access_token

# Database Configuration
DYNAMODB_TABLE_PREFIX=ai-nutritionist-prod

# AWS Configuration
AWS_REGION=us-east-1
```

### 3. DynamoDB Tables

The application creates these DynamoDB tables:
- `ai-nutritionist-users`
- `ai-nutritionist-meals`
- `ai-nutritionist-subscriptions`
- `ai-nutritionist-usage-tracking`

## Monitoring and Logging

### 1. CloudWatch Logs

View application logs:

```bash
# View logs for a specific function
sam logs -n NutritionWebhookFunction --tail

# View logs with filter
sam logs -n NutritionWebhookFunction --filter "ERROR"
```

### 2. CloudWatch Metrics

Monitor these key metrics:
- Lambda function duration
- Lambda function errors
- API Gateway 4xx/5xx errors
- DynamoDB read/write capacity

### 3. X-Ray Tracing

Enable X-Ray tracing in `template.yaml`:

```yaml
Globals:
  Function:
    Tracing: Active
```

## Security Configuration

### 1. IAM Roles and Policies

The SAM template creates IAM roles with minimal required permissions:
- DynamoDB read/write access
- CloudWatch Logs write access
- X-Ray tracing permissions

### 2. API Gateway Security

Configure API Gateway with:
- Request validation
- Rate limiting
- CORS settings
- API keys (if needed)

### 3. Environment Variables Encryption

Use AWS KMS to encrypt sensitive environment variables:

```yaml
Environment:
  Variables:
    OPENAI_API_KEY: 
      Ref: OpenAIApiKeyParameter
```

## Troubleshooting

### Common Deployment Issues

#### Build Failures

```bash
# Clean and rebuild
sam build --use-container --debug

# For dependency issues
pip install --upgrade aws-sam-cli
```

#### Permission Errors

```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify IAM permissions for CloudFormation, Lambda, API Gateway
```

#### Timeout Issues

```bash
# Increase timeout in template.yaml
Timeout: 30  # seconds

# For large dependencies, use container builds
sam build --use-container
```

### Debugging Deployed Functions

#### Local Testing

```bash
# Test functions locally
sam local start-api

# Invoke specific function
sam local invoke NutritionWebhookFunction --event events/test-event.json
```

#### Remote Debugging

```bash
# View recent logs
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/ai-nutritionist

# Stream live logs
aws logs tail /aws/lambda/ai-nutritionist-NutritionWebhookFunction --follow
```

## Rollback Procedures

### 1. CloudFormation Rollback

```bash
# Rollback to previous version
aws cloudformation cancel-update-stack --stack-name ai-nutritionist-prod

# Delete problematic stack (if needed)
aws cloudformation delete-stack --stack-name ai-nutritionist-prod
```

### 2. Function-Level Rollback

```bash
# List function versions
aws lambda list-versions-by-function --function-name ai-nutritionist-webhook

# Update alias to previous version
aws lambda update-alias --function-name ai-nutritionist-webhook --name LIVE --function-version 1
```

## Performance Optimization

### 1. Lambda Optimization

- Use appropriate memory allocation (128MB - 3008MB)
- Enable provisioned concurrency for frequently used functions
- Optimize cold start times with smaller deployment packages

### 2. DynamoDB Optimization

- Use on-demand billing for variable workloads
- Implement proper partition key design
- Enable DynamoDB Accelerator (DAX) for read-heavy workloads

### 3. API Gateway Optimization

- Enable caching for frequently accessed endpoints
- Use compression for large responses
- Implement proper throttling limits

## Cleanup

### Remove Deployment

```bash
# Delete the CloudFormation stack
sam delete --stack-name ai-nutritionist-prod

# Verify deletion
aws cloudformation describe-stacks --stack-name ai-nutritionist-prod
```

### Manual Cleanup

Some resources may need manual deletion:
- S3 buckets (if not empty)
- DynamoDB tables (if deletion protection enabled)
- CloudWatch log groups
- Parameter Store parameters

## CI/CD Pipeline Integration

### GitHub Actions Example

```yaml
name: Deploy AI Nutritionist
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.11
      
      - name: Install dependencies
        run: |
          pip install aws-sam-cli
          pip install -r requirements.txt
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Build and deploy
        run: |
          sam build
          sam deploy --no-confirm-changeset --no-fail-on-empty-changeset
```

## Best Practices

1. **Use separate environments** (dev, staging, prod)
2. **Implement proper monitoring** and alerting
3. **Regular security updates** for dependencies
4. **Backup strategy** for DynamoDB data
5. **Cost monitoring** and optimization
6. **Documentation updates** with each deployment
7. **Testing in staging** before production deployment
8. **Rollback plan** for each deployment

---

For additional support, refer to:
- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [AWS CloudFormation Documentation](https://docs.aws.amazon.com/cloudformation/)
