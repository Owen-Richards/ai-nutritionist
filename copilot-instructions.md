# AI Nutritionist Assistant - Copilot Instructions

## Project Overview
This is a serverless AI-powered WhatsApp/SMS nutritionist bot built with AWS Lambda, DynamoDB, and Bedrock AI. The system provides personalized meal planning, nutrition advice, and grocery lists through natural language conversations.

## Architecture
- **Frontend**: WhatsApp/SMS via Twilio API
- **Backend**: AWS Lambda (Python 3.11) with API Gateway
- **Database**: DynamoDB with TTL for GDPR compliance
- **AI Service**: AWS Bedrock (Amazon Titan Text Express)
- **Infrastructure**: AWS SAM (Serverless Application Model)
- **Monitoring**: CloudWatch Logs and X-Ray tracing

## Key Files and Responsibilities

### Infrastructure
- `infrastructure/template.yaml` - AWS SAM CloudFormation template defining all resources
- `.vscode/tasks.json` - VS Code tasks for development workflow
- `.vscode/launch.json` - Debug configurations

### Application Code
- `src/handlers/message_handler.py` - Main webhook handler for Twilio messages
- `src/handlers/scheduler_handler.py` - EventBridge-triggered meal plan automation
- `src/services/ai_service.py` - AWS Bedrock integration for AI responses
- `src/services/user_service.py` - DynamoDB user profile management
- `src/services/meal_plan_service.py` - Meal planning orchestration
- `src/services/aws_sms_service.py` - AWS End User Messaging API wrapper (replaces Twilio)

### Configuration & Data
- `src/data/sample-twilio-webhook.json` - Example webhook payload for testing
- `requirements.txt` - Python dependencies
- `pyproject.toml` - Python project configuration
- `.env.template` - Environment variables template

### Testing
- `tests/test_*.py` - Unit tests for all services
- `tests/test_project_validation.py` - Project structure validation

## Development Guidelines

### Code Style
- Use Black for code formatting
- Follow PEP 8 conventions
- Include comprehensive docstrings
- Add type hints where appropriate

### Error Handling
- Use structured logging with correlation IDs
- Implement graceful degradation for AI service failures
- Validate all inputs from external sources (Twilio webhooks)
- Return user-friendly error messages

### Security
- Validate Twilio webhook signatures
- Sanitize all user inputs
- Use AWS IAM least privilege principles
- Store secrets in AWS Systems Manager Parameter Store

### Testing
- Mock external services (AWS, Twilio) in unit tests
- Include edge cases and error conditions
- Validate both successful and failure scenarios
- Use pytest fixtures for common test data

### AI Integration
- Design prompts for cost efficiency
- Implement response parsing with fallbacks
- Cache meal plans to reduce AI API calls
- Handle AI service rate limits and errors

## Common Development Tasks

### Local Development
1. Activate virtual environment: `.venv/Scripts/activate`
2. Install dependencies: Use "Install Dependencies" VS Code task
3. Run tests: Use "Run Tests" VS Code task
4. Format code: Use "Format Code" VS Code task

### AWS Deployment
1. Configure AWS CLI with appropriate permissions
2. Install AWS SAM CLI
3. Build: `sam build`
4. Deploy: `sam deploy --guided`

### Adding New Features
1. Update the SAM template if new AWS resources needed
2. Add service layer code in `src/services/`
3. Update handler code in `src/handlers/`
4. Add comprehensive tests
5. Update documentation

## Environment Variables
- AWS_DEFAULT_REGION: AWS region for all services
- DYNAMODB_TABLE_NAME: User data table name
- TWILIO_* variables: Retrieved from Parameter Store in production
- BEDROCK_MODEL_ID: AI model identifier

## Common Issues & Solutions

### Testing Issues
- Use `configure_python_environment` before running tests
- Mock AWS services properly to avoid region/credential errors
- Use `test_project_validation.py` for quick structure checks

### Deployment Issues
- Ensure AWS CLI is configured with proper permissions
- Check CloudFormation stack events for detailed error info
- Verify Parameter Store values are set correctly

### AI Service Issues
- Monitor CloudWatch logs for Bedrock API errors
- Implement fallback responses for AI failures
- Check token limits and adjust prompts accordingly

## Best Practices
- Always validate user input before processing
- Use correlation IDs for request tracking
- Implement idempotency for message processing
- Cache frequently accessed data
- Monitor costs and optimize AI usage
- Follow AWS Well-Architected Framework principles

## External Dependencies
- Twilio WhatsApp Business API
- AWS Bedrock AI service
- AWS DynamoDB
- AWS Lambda runtime
- AWS API Gateway

## Useful VS Code Commands
- Ctrl+Shift+P → "Tasks: Run Task" for development tasks
- F5 to start debugging with configured launch options
- Ctrl+` to open integrated terminal
- Ctrl+Shift+` to create new terminal
