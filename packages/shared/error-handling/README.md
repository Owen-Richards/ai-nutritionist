# Comprehensive Error Handling System

A production-ready error handling framework that provides robust error management, recovery strategies, and monitoring across all services in the AI Nutritionist application.

## 🌟 Features

### Exception Hierarchy

- **BaseError**: Root exception with context, severity, and user messages
- **DomainError**: Business rule violations
- **ValidationError**: Input validation failures
- **NotFoundError**: Resource not found errors
- **ConflictError**: State conflicts and concurrency issues
- **InfrastructureError**: External service failures
- **AuthenticationError**: Authentication failures
- **AuthorizationError**: Authorization failures
- **RateLimitError**: Rate limiting errors
- **PaymentError**: Payment processing errors

### Error Handling Middleware

- **Global Exception Handler**: Catches and formats all errors
- **Circuit Breaker Pattern**: Prevents cascading failures
- **Retry Logic**: Exponential backoff with jitter
- **Graceful Degradation**: Fallback responses when services fail
- **Error Recovery**: Intelligent recovery strategies

### Monitoring & Analytics

- **Error Metrics**: CloudWatch integration for monitoring
- **Error Analytics**: Trend analysis and insights
- **Health Checks**: System health based on error patterns
- **Alerting**: Automatic alerts for critical errors

## 🚀 Quick Start

### 1. Import the Error Handling System

```python
from packages.shared.error_handling import (
    BaseError, DomainError, ValidationError,
    error_handler, circuit_breaker, retry_with_backoff,
    ErrorRecoveryManager, ErrorFormatter
)
```

### 2. Basic Error Handling

```python
@error_handler(log_errors=True, collect_metrics=True)
@retry_with_backoff(max_retries=3)
async def my_service_function(user_id: str) -> Dict[str, Any]:
    # Input validation
    if not user_id:
        raise ValidationError(
            message="User ID is required",
            field="user_id",
            invalid_value=user_id
        )

    # Business logic
    result = await external_service_call(user_id)
    return result
```

### 3. Circuit Breaker Protection

```python
@circuit_breaker(failure_threshold=5, recovery_timeout=60)
async def unreliable_external_service():
    # This will open the circuit after 5 failures
    # and try again after 60 seconds
    pass
```

### 4. Recovery Manager

```python
recovery_manager = ErrorRecoveryManager()

result = await recovery_manager.execute_with_recovery(
    func=external_api_call,
    operation_name="get_nutrition_data",
    fallback_type="nutrition_advice",
    user_id=user_id
)
```

## 📋 Usage Examples

### Service-Level Error Handling

```python
class NutritionService:
    def __init__(self):
        self.recovery_manager = ErrorRecoveryManager()
        self.error_formatter = ErrorFormatter()

    @error_handler(log_errors=True, collect_metrics=True)
    async def generate_meal_plan(self, user_id: str, preferences: Dict) -> Dict:
        # Validation
        if not user_id:
            raise ValidationError("User ID required", field="user_id")

        # Business rules
        calories = preferences.get('calories', 0)
        if calories < 800 or calories > 5000:
            raise DomainError(
                "Calorie target outside healthy range",
                business_rule="healthy_calorie_range"
            )

        # External service with recovery
        result = await self.recovery_manager.execute_with_recovery(
            func=self._call_ai_service,
            operation_name="generate_meal_plan",
            fallback_type="meal_plan",
            user_id=user_id,
            preferences=preferences
        )

        return result['data'] if result['success'] else self._get_fallback()
```

### API Handler Integration

```python
async def lambda_handler(event, context):
    error_formatter = ErrorFormatter()

    try:
        # Process request
        result = await process_request(event)
        return {
            'statusCode': 200,
            'body': json.dumps({'success': True, 'data': result})
        }

    except ValidationError as e:
        response = error_formatter.format_for_api(e)
        return {'statusCode': 400, 'body': json.dumps(response)}

    except BaseError as e:
        response = error_formatter.format_for_api(e)
        return {'statusCode': 500, 'body': json.dumps(response)}
```

### Chat/Messaging Error Handling

```python
class ChatHandler:
    def __init__(self):
        self.error_formatter = ErrorFormatter()

    async def handle_message(self, user_id: str, message: str) -> str:
        try:
            return await self.process_message(user_id, message)

        except RateLimitError as e:
            return f"Whoa there! 🐌 {e.user_message}"

        except BaseError as e:
            return self.error_formatter.format_for_user(e, context="chat")

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return "Oops! Something went wrong. Let me try again! 😅"
```

## 🛡️ Error Types and When to Use Them

### ValidationError

Use for input validation failures:

```python
if not email or '@' not in email:
    raise ValidationError(
        message="Invalid email format",
        field="email",
        invalid_value=email,
        validation_rules=["required", "email_format"]
    )
```

### DomainError

Use for business rule violations:

```python
if age < 13:
    raise DomainError(
        message="Age must be 13 or older",
        business_rule="minimum_age_requirement",
        context={'min_age': 13, 'provided_age': age}
    )
```

### NotFoundError

Use when resources don't exist:

```python
user = await get_user(user_id)
if not user:
    raise NotFoundError(
        message="User not found",
        resource_type="user",
        resource_id=user_id
    )
```

### InfrastructureError

Use for external service failures:

```python
try:
    response = await external_api_call()
except requests.RequestException as e:
    raise InfrastructureError(
        message="External service unavailable",
        service_name="openai",
        operation="chat_completion",
        cause=e
    )
```

### PaymentError

Use for payment-related failures:

```python
try:
    charge = stripe.Charge.create(...)
except stripe.error.CardError as e:
    raise PaymentError(
        message="Card was declined",
        payment_method=payment_method_id,
        amount=amount,
        provider_error_code=e.code
    )
```

## 🔄 Recovery Strategies

### Retry with Backoff

```python
@retry_with_backoff(
    max_retries=3,
    base_delay=1.0,
    backoff_multiplier=2.0,
    retryable_exceptions=(InfrastructureError, ConnectionError)
)
async def api_call():
    # Will retry up to 3 times with exponential backoff
    pass
```

### Circuit Breaker

```python
@circuit_breaker(
    failure_threshold=5,    # Open after 5 failures
    recovery_timeout=60     # Try again after 60 seconds
)
async def unreliable_service():
    # Circuit will open after repeated failures
    pass
```

### Fallback Responses

```python
# Define fallbacks in ErrorRecoveryManager
recovery_manager.add_fallback_response('meal_plan', {
    'success': True,
    'meal_plan': {
        'breakfast': {'name': 'Oatmeal', 'calories': 300},
        'lunch': {'name': 'Salad', 'calories': 400},
        'dinner': {'name': 'Chicken', 'calories': 500}
    },
    'fallback': True
})
```

## 📊 Monitoring and Analytics

### Error Metrics

```python
metrics_collector = ErrorMetricsCollector()

# Automatic collection with decorators
@error_handler(collect_metrics=True)
async def my_function():
    pass

# Manual collection
metrics_collector.record_error(error, context={'user_id': user_id})
```

### Analytics Dashboard

```python
# Get error analytics
analytics = metrics_collector.get_error_analytics(time_window_hours=24)

print(f"Total errors: {analytics['total_errors']}")
print(f"Error rate: {analytics['error_rate']}/hour")
print(f"Top errors: {analytics['top_error_codes']}")
print(f"Insights: {analytics['insights']}")
```

### Health Checks

```python
class HealthCheckService:
    async def get_health_status(self):
        analytics = self.metrics_collector.get_error_analytics(1)

        if analytics['total_errors'] > 50:
            return {'status': 'degraded', 'reason': 'High error rate'}

        return {'status': 'healthy'}
```

## 🎨 User-Friendly Messages

### Automatic Message Generation

```python
error = ValidationError("Email is required", field="email")
formatter = ErrorFormatter()

# For API responses
api_message = formatter.format_for_api(error)
# {"error": True, "message": "There seems to be an issue with your input..."}

# For chat interfaces
chat_message = formatter.format_for_user(error, context="chat")
# "Hmm... 🤔 There seems to be an issue with your input..."

# For email notifications
email_data = format_error_for_email(error, user_name="John")
# {"subject": "Issue with your request", "body": "Hi John, ..."}
```

### Custom Messages by Context

```python
# Nutrition-specific messages
UserFriendlyMessages.NUTRITION_MESSAGES = {
    'meal_plan_error': "I couldn't generate your meal plan right now. Here's a basic plan! 🍽️",
    'ingredient_not_found': "I couldn't find that ingredient. Try a similar one? 🔍"
}
```

## 🔧 Integration with Existing Services

### 1. Update Service Classes

```python
# Before
class MyService:
    def process_data(self, data):
        try:
            result = external_api_call(data)
            return result
        except Exception as e:
            logger.error(f"Error: {e}")
            return None

# After
class MyService:
    def __init__(self):
        self.recovery_manager = ErrorRecoveryManager()

    @error_handler(log_errors=True, collect_metrics=True)
    @retry_with_backoff(max_retries=3)
    async def process_data(self, data):
        if not data:
            raise ValidationError("Data is required", field="data")

        result = await self.recovery_manager.execute_with_recovery(
            func=external_api_call,
            operation_name="process_data",
            fallback_type="data_processing",
            data=data
        )

        return result
```

### 2. Update Lambda Handlers

```python
# Use the enhanced_lambda_handler template from integration.py
async def lambda_handler(event, context):
    error_formatter = ErrorFormatter()

    try:
        # Your handler logic
        pass
    except BaseError as e:
        response = error_formatter.format_for_api(e)
        return {
            'statusCode': 500,
            'body': json.dumps(response),
            'headers': {'X-Error-ID': e.error_id}
        }
```

### 3. Add to Existing Middleware

```python
# Add ErrorHandlingMiddleware to your ASGI/WSGI app
from packages.shared.error_handling import ErrorHandlingMiddleware

app = ErrorHandlingMiddleware(
    app=your_app,
    enable_metrics=True,
    enable_user_friendly_messages=True,
    include_error_details=False  # Set True for development
)
```

## 📈 Performance Impact

### Minimal Overhead

- **Decorators**: < 1ms overhead per function call
- **Error Creation**: < 0.1ms for exception instantiation
- **Metrics Collection**: Async, non-blocking
- **Circuit Breakers**: In-memory state, microsecond checks

### Optimization Tips

- Use circuit breakers for frequently failing services
- Set appropriate retry limits to avoid excessive delays
- Enable metrics collection only in production
- Use fallback responses for critical user-facing operations

## 🚨 Common Patterns

### Handling External API Failures

```python
@circuit_breaker(failure_threshold=3)
@retry_with_backoff(max_retries=2)
async def call_openai_api(prompt):
    try:
        response = await openai.ChatCompletion.acreate(...)
        return response
    except openai.error.RateLimitError as e:
        raise InfrastructureError(
            "OpenAI rate limit exceeded",
            service_name="openai",
            retry_after=60
        )
```

### Database Transaction Errors

```python
async def update_user_profile(user_id, data):
    try:
        async with database.transaction():
            await update_user(user_id, data)
            await log_update(user_id)
    except IntegrityError as e:
        raise ConflictError(
            "Profile update conflicts with existing data",
            conflicting_resource="user_profile"
        )
```

### Payment Processing

```python
async def process_payment(amount, payment_method):
    if amount <= 0:
        raise ValidationError("Amount must be positive", field="amount")

    try:
        charge = await stripe.Charge.create(...)
        return charge
    except stripe.error.CardError as e:
        raise PaymentError(
            "Payment failed",
            amount=amount,
            payment_method=payment_method,
            provider_error_code=e.code
        )
```

## 🧪 Testing Error Handling

### Unit Tests

```python
import pytest
from packages.shared.error_handling import ValidationError

async def test_validation_error():
    with pytest.raises(ValidationError) as exc_info:
        await my_service.process_data(invalid_data)

    assert exc_info.value.field == "email"
    assert "required" in exc_info.value.validation_rules
```

### Integration Tests

```python
async def test_service_with_fallback():
    # Mock external service failure
    with mock.patch('external_service.call', side_effect=Exception()):
        result = await my_service.get_data()

        # Should return fallback response
        assert result['fallback'] is True
        assert result['success'] is True
```

## 📚 Best Practices

### 1. Error Hierarchy

- Use specific error types for different failure modes
- Include relevant context in error objects
- Set appropriate severity levels

### 2. User Messages

- Always provide user-friendly messages
- Avoid exposing technical details to end users
- Include actionable guidance when possible

### 3. Recovery Strategies

- Implement fallbacks for critical user-facing operations
- Use circuit breakers for unreliable external services
- Set reasonable retry limits to avoid excessive delays

### 4. Monitoring

- Enable error metrics collection in production
- Set up alerts for critical error conditions
- Review error analytics regularly for trends

### 5. Logging

- Use structured logging with error context
- Include correlation IDs for request tracing
- Log at appropriate levels based on error severity

## 🔧 Configuration

### Environment Variables

```bash
# Error handling configuration
ERROR_METRICS_ENABLED=true
ERROR_DETAILS_INCLUDE=false
CIRCUIT_BREAKER_ENABLED=true
RETRY_MAX_ATTEMPTS=3
FALLBACK_RESPONSES_ENABLED=true

# CloudWatch metrics
AWS_REGION=us-east-1
CLOUDWATCH_NAMESPACE=AINutritionist/Errors

# DynamoDB error storage
ERROR_TABLE_NAME=ai-nutritionist-error-metrics
```

### Service Configuration

```python
# Configure recovery manager
recovery_manager = ErrorRecoveryManager()

# Add custom error patterns
recovery_manager.add_error_pattern('custom_timeout', ErrorPattern(
    error_type='custom_timeout',
    patterns=['custom timeout', 'service timeout'],
    recovery_config=RecoveryConfig(
        strategy=RecoveryStrategy.CIRCUIT_BREAKER,
        max_retries=2
    )
))

# Add custom fallback responses
recovery_manager.add_fallback_response('custom_service', {
    'success': True,
    'data': 'fallback_data',
    'fallback': True
})
```

## 🆘 Troubleshooting

### Common Issues

**Issue**: Errors not being caught by middleware

- **Solution**: Ensure ErrorHandlingMiddleware is properly configured in your ASGI/WSGI app

**Issue**: Circuit breaker not opening despite failures

- **Solution**: Check that exceptions are being properly categorized and counted

**Issue**: Retry logic causing long delays

- **Solution**: Adjust max_retries and backoff_multiplier parameters

**Issue**: Error metrics not appearing in CloudWatch

- **Solution**: Verify AWS credentials and IAM permissions for CloudWatch

### Debug Mode

```python
# Enable debug logging
import logging
logging.getLogger('packages.shared.error_handling').setLevel(logging.DEBUG)

# Include error details in responses
error_formatter = ErrorFormatter(include_debug_info=True)
```

## 📖 API Reference

See the individual module files for complete API documentation:

- `exceptions.py` - Exception classes and utilities
- `middleware.py` - Decorators and middleware
- `recovery.py` - Recovery manager and strategies
- `formatters.py` - Error formatting and user messages
- `metrics.py` - Metrics collection and analytics

## 🤝 Contributing

When adding new error types or recovery strategies:

1. Follow the existing naming conventions
2. Include comprehensive docstrings
3. Add user-friendly messages to UserFriendlyMessages
4. Update the examples and integration templates
5. Add appropriate unit tests

## 📄 License

This error handling system is part of the AI Nutritionist application and follows the same license terms.
