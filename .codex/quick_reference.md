# Codex Integration Quick Reference

## Project Overview

**AI Nutritionist Assistant** - Serverless AI-powered nutrition coaching platform built on AWS with clean architecture principles.

## Quick Context for AI Assistance

### Architecture Pattern

- **Clean Architecture** with dependency injection
- **AWS Serverless** (Lambda, API Gateway, DynamoDB)
- **Event-driven** messaging with Amazon Pinpoint
- **AI-powered** using AWS Bedrock (Claude/Titan models)

### Key Directories

```
src/
├── core/           # Domain entities and interfaces
├── services/       # Business logic (meal planning, nutrition, messaging)
├── adapters/       # AWS service integrations (Bedrock, DynamoDB, Pinpoint)
├── api/           # FastAPI web layer
├── handlers/      # Lambda function handlers
├── models/        # Pydantic data models
└── config/        # Environment and settings management
```

### Common Patterns

#### Service Dependency Injection

```python
class MealPlanService:
    def __init__(self, ai_service: AIService, nutrition_repo: NutritionRepository):
        self.ai_service = ai_service
        self.nutrition_repo = nutrition_repo
```

#### Lambda Handler Structure

```python
async def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        # Parse event
        request = parse_request(event)

        # Business logic
        result = await service.process(request)

        # Return response
        return success_response(result)
    except Exception as e:
        return error_response(str(e))
```

#### AWS Service Integration

```python
# Bedrock AI
bedrock_runtime = boto3.client('bedrock-runtime')
response = bedrock_runtime.invoke_model(
    modelId="anthropic.claude-3-haiku-20240307-v1:0",
    body=json.dumps(payload)
)

# DynamoDB
table = dynamodb.Table('ai-nutritionist-users-dev')
table.put_item(Item=item)

# Pinpoint Messaging
pinpoint = boto3.client('pinpoint')
pinpoint.send_messages(
    ApplicationId=app_id,
    MessageRequest=message_request
)
```

### Environment Variables

```bash
# Core Services
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
PINPOINT_APPLICATION_ID=your-app-id

# DynamoDB Tables
DYNAMODB_USER_TABLE=ai-nutritionist-users-dev
DYNAMODB_MEAL_PLANS_TABLE=ai-nutritionist-meal-plans-dev
DYNAMODB_PROMPT_CACHE_TABLE=ai-nutritionist-prompt-cache-dev

# Feature Flags
ENABLE_PROMPT_CACHING=true
ENABLE_COST_OPTIMIZATION=true
LOG_LEVEL=INFO
```

### Testing Patterns

```python
# Unit test with mocks
@pytest.fixture
def mock_bedrock():
    with patch('boto3.client') as mock:
        yield mock.return_value

async def test_generate_meal_plan(mock_bedrock):
    mock_bedrock.invoke_model.return_value = {'body': MagicMock()}
    # Test implementation
```

### Common Models

```python
@dataclass
class UserProfile:
    user_id: str
    dietary_preferences: List[str]
    health_goals: Dict[str, Any]
    budget_constraints: Optional[float] = None

@dataclass
class MealPlan:
    plan_id: UUID
    user_id: str
    meals: List[Dict[str, Any]]
    nutrition_summary: Dict[str, float]
    created_at: datetime
```

### Error Handling

```python
class AINutritionistError(Exception):
    """Base application exception"""
    pass

class ValidationError(AINutritionistError):
    """Input validation errors"""
    pass

class ExternalServiceError(AINutritionistError):
    """External service integration errors"""
    pass
```

### Logging Pattern

```python
import logging
logger = logging.getLogger(__name__)

# Structured logging
logger.info("Processing meal plan request", extra={
    "user_id": user_id,
    "request_type": "meal_plan_generation",
    "preferences": preferences
})
```

## Development Workflow

### Setup

```bash
python -m venv .venv
.venv/Scripts/activate  # Windows
pip install -r requirements.txt
```

### Testing

```bash
pytest tests/ -v                    # All tests
pytest tests/unit/ -v              # Unit tests only
pytest tests/integration/ -v       # Integration tests
```

### Deployment

```bash
sam build                         # Build SAM application
sam deploy --guided              # Deploy to AWS
```

### Local Development

```bash
sam local start-api              # Start local API Gateway
sam local invoke FunctionName    # Test specific Lambda
```

## Key Business Domains

### Meal Planning Service

- AI-powered meal plan generation
- Nutritional analysis and optimization
- Budget-aware recipe selection
- Dietary restriction compliance

### Messaging Service

- Multi-channel messaging (WhatsApp, SMS)
- Conversation state management
- Message routing and delivery
- Rate limiting and spam protection

### User Personalization

- Preference learning and adaptation
- Goal tracking and progress monitoring
- Behavioral analytics
- Recommendation engine

### Business Services

- Subscription and billing management
- Usage tracking and cost optimization
- Analytics and reporting
- Gamification and engagement

## Security Considerations

- **Input Validation**: Pydantic models for all inputs
- **Authentication**: AWS Cognito integration
- **Authorization**: IAM roles and policies
- **Data Encryption**: KMS encryption at rest
- **Rate Limiting**: API Gateway throttling
- **Audit Logging**: CloudTrail and application logs

## Performance Optimizations

- **Prompt Caching**: Bedrock response caching
- **Connection Pooling**: Reuse AWS service clients
- **Async Processing**: asyncio for concurrent operations
- **CDN**: CloudFront for static content
- **Database Optimization**: DynamoDB single-table design
