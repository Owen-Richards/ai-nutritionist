# AI Nutritionist Assistant - Development Setup

## Prerequisites

Before you can run this project locally, ensure you have:

1. **Python 3.11+** installed
2. **AWS CLI** configured with your credentials
3. **AWS SAM CLI** installed
4. **Twilio account** with WhatsApp Business API access

## Initial Setup

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure AWS Services

#### Set up AWS Parameters for Twilio
```bash
# Twilio Account SID
aws ssm put-parameter \
  --name "/ai-nutritionist/twilio/account-sid" \
  --value "your-twilio-account-sid" \
  --type "String"

# Twilio Auth Token (encrypted)
aws ssm put-parameter \
  --name "/ai-nutritionist/twilio/auth-token" \
  --value "your-twilio-auth-token" \
  --type "SecureString"

# Twilio Phone Number
aws ssm put-parameter \
  --name "/ai-nutritionist/twilio/phone-number" \
  --value "+1234567890" \
  --type "String"
```

#### Enable Bedrock Models
Ensure these models are enabled in your AWS account:
- `amazon.titan-text-express-v1`
- `anthropic.claude-3-haiku-20240307-v1:0` (optional, for premium features)

### 3. Deploy Infrastructure

```bash
# Navigate to infrastructure directory
cd infrastructure

# Build the SAM application
sam build

# Deploy with guided setup (first time)
sam deploy --guided

# For subsequent deployments
sam deploy
```

### 4. Configure Twilio Webhook

After deployment, get your API Gateway URL from the SAM output and configure it in your Twilio console:

1. Go to Twilio Console → WhatsApp → Sandbox Settings
2. Set webhook URL to: `https://your-api-gateway-url/webhook`
3. Set HTTP method to: `POST`

## Local Development

### Running Locally

```bash
# Start local API Gateway
sam local start-api --port 3000

# In another terminal, test with sample event
sam local invoke MessageHandlerFunction \
  --event src/data/sample-twilio-webhook.json
```

### Testing

```bash
# Run unit tests
pytest tests/

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_ai_service.py -v
```

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

## Environment Variables

For local development, create a `.env` file (not committed to git):

```bash
# .env
DYNAMODB_TABLE=ai-nutritionist-users-dev
BEDROCK_REGION=us-east-1
AWS_DEFAULT_REGION=us-east-1
```

## Useful Commands

### AWS SAM Commands

```bash
# Build and deploy
sam build && sam deploy

# Delete stack
sam delete

# View logs
sam logs -n MessageHandlerFunction --tail

# Generate test events
sam local generate-event apigateway aws-proxy > test-event.json
```

### Database Operations

```bash
# List DynamoDB tables
aws dynamodb list-tables

# Scan user table (development only!)
aws dynamodb scan --table-name ai-nutritionist-users-dev

# Delete test user
aws dynamodb delete-item \
  --table-name ai-nutritionist-users-dev \
  --key '{"user_id":{"S":"1234567890"},"plan_date":{"S":"profile"}}'
```

### Parameter Store Operations

```bash
# List parameters
aws ssm get-parameters-by-path --path "/ai-nutritionist/"

# Update parameter
aws ssm put-parameter \
  --name "/ai-nutritionist/twilio/auth-token" \
  --value "new-token" \
  --type "SecureString" \
  --overwrite
```

## Troubleshooting

### Common Issues

1. **"Import boto3 could not be resolved"**
   - Install dependencies: `pip install -r requirements.txt`
   - Activate virtual environment

2. **"Access Denied" when calling Bedrock**
   - Ensure Bedrock models are enabled in your AWS region
   - Check IAM permissions for your AWS profile

3. **Twilio webhook not receiving messages**
   - Verify webhook URL is correct
   - Check API Gateway logs
   - Ensure Twilio signature validation is working

4. **DynamoDB table not found**
   - Deploy infrastructure: `sam deploy`
   - Check table name in AWS console

### Debugging

#### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Check CloudWatch Logs
```bash
# View Lambda logs
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/ai-nutritionist"

# Tail logs
sam logs -n MessageHandlerFunction --tail
```

#### Test Individual Services
```python
# Test AI service locally
from src.services.ai_service import AIService

ai_service = AIService()
user_profile = {
    'dietary_restrictions': ['vegetarian'],
    'household_size': 2,
    'weekly_budget': 50
}
meal_plan = ai_service.generate_meal_plan(user_profile)
print(meal_plan)
```

## Development Workflow

1. **Create feature branch**
   ```bash
   git checkout -b feature/new-feature
   ```

2. **Make changes and test**
   ```bash
   # Run tests
   pytest
   
   # Test locally
   sam local start-api
   ```

3. **Deploy to development**
   ```bash
   sam deploy --parameter-overrides Environment=dev
   ```

4. **Create pull request**
   ```bash
   git push origin feature/new-feature
   ```

## Production Deployment

### Environment-Specific Deployments

```bash
# Development
sam deploy --parameter-overrides Environment=dev

# Staging  
sam deploy --parameter-overrides Environment=staging

# Production
sam deploy --parameter-overrides Environment=prod
```

### Monitoring

- **CloudWatch Dashboard**: Monitor Lambda metrics, API Gateway requests
- **X-Ray Tracing**: Enable for performance insights
- **Cost Monitoring**: Set up billing alerts

## Security Checklist

- [ ] Twilio webhook signature validation enabled
- [ ] API keys stored in Parameter Store/Secrets Manager
- [ ] IAM roles follow least privilege principle
- [ ] DynamoDB encryption at rest enabled
- [ ] CloudWatch Logs encryption enabled (optional)
- [ ] No secrets in code or git history

## Performance Optimization

### Cost Optimization
- Use Bedrock prompt caching
- Implement meal plan caching
- Monitor token usage
- Set Lambda memory appropriately

### Latency Optimization
- Keep Lambda functions warm
- Optimize DynamoDB queries
- Use connection pooling for external APIs

## Next Steps

1. Set up CI/CD pipeline with GitHub Actions
2. Add monitoring and alerting
3. Implement calendar integration
4. Add recipe API integration
5. Build web interface for user management
