# Structured Logging Implementation Examples

This directory contains comprehensive examples of structured logging implementation across all layers of the AI Nutritionist application.

## Overview

The structured logging framework provides:

- **JSON structured logging** with correlation ID tracking
- **Performance metrics** and business event logging
- **PII masking** for GDPR compliance
- **CloudWatch integration** for log aggregation
- **Distributed tracing** with AWS X-Ray
- **Health monitoring** and alerting
- **Audit logging** for compliance

## Examples

### 1. API Layer Logging (`api_logging_example.py`)

Demonstrates comprehensive API logging including:

- **Request/Response Logging**: Automatic logging of all HTTP requests and responses
- **Performance Monitoring**: Track response times and throughput
- **Security Logging**: Authentication failures and unauthorized access attempts
- **Business Event Tracking**: User actions and business operations
- **Error Handling**: Structured error logging with context

Key Features:

```python
# Automatic request logging with correlation IDs
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    # Logs request details, tracks performance, handles errors

# Business event logging
@audit_log(EventType.USER_ACTION, "nutrition", "analyze")
async def analyze_nutrition(request: Dict[str, Any]):
    # Automatic audit logging for business operations
```

### 2. Domain Service Logging (`domain_service_logging_example.py`)

Shows how to implement logging in domain services:

- **Business Logic Logging**: Track domain operations and decisions
- **Data Validation Logging**: Log validation failures and data quality issues
- **Performance Tracking**: Monitor operation duration and resource usage
- **Domain Event Logging**: Track business events and state changes

Key Features:

```python
@performance_monitor("nutrition_analysis")
@audit_log(EventType.BUSINESS_EVENT, "nutrition", "analyze_meal")
async def analyze_meal(food_items: List[FoodItem], user_id: str):
    # Comprehensive business operation logging

# Context managers for operation tracking
with logger.operation_context("meal_analysis") as ctx:
    # Automatic performance tracking and correlation
```

### 3. Infrastructure Layer Logging (`infrastructure_logging_example.py`)

Demonstrates infrastructure-level logging:

- **Database Operation Logging**: Track queries, performance, and failures
- **External API Logging**: Monitor third-party service calls
- **Caching Operation Logging**: Track cache hits, misses, and performance
- **AWS Service Logging**: Monitor S3, DynamoDB, and other AWS operations

Key Features:

```python
# Database operation logging
@performance_monitor("db_query")
async def get_user_by_id(user_id: str):
    # Automatic database performance tracking

# External API monitoring
async def get_food_nutrition_data(food_name: str):
    # Comprehensive external service monitoring
```

### 4. CloudWatch Integration (`cloudwatch_integration_example.py`)

Shows complete CloudWatch integration setup:

- **Log Groups and Retention**: Automated log group creation with retention policies
- **Metric Filters**: Extract metrics from log data
- **CloudWatch Alarms**: Automated alerting for system health
- **Dashboards**: Real-time monitoring dashboards
- **X-Ray Tracing**: Distributed tracing setup

## Quick Start

### 1. Basic Setup

```python
from packages.shared.monitoring.setup import setup_service_monitoring

# Setup monitoring for your service
monitoring = setup_service_monitoring("your-service-name")

# Get logger instance
logger = monitoring.get_logger()

# Basic logging
logger.info("Service started", extra={"version": "1.0.0"})
```

### 2. Environment Configuration

Set environment variables for production:

```bash
# Logging
export LOG_LEVEL=INFO
export USE_CLOUDWATCH_LOGS=true
export CLOUDWATCH_LOG_GROUP=/ai-nutritionist/your-service

# Metrics
export USE_CLOUDWATCH_METRICS=true
export METRICS_NAMESPACE=AI-Nutritionist

# Tracing
export USE_XRAY=true

# Health checks
export ENABLE_HEALTH_CHECKS=true
export HEALTH_CHECK_INTERVAL=60

# AWS
export AWS_REGION=us-east-1
```

### 3. Development vs Production

**Development:**

```python
config = MonitoringConfig(
    service_name="your-service",
    environment="development",
    log_level=LogLevel.DEBUG,
    use_cloudwatch_logs=False,
    use_cloudwatch_metrics=False,
    use_xray=False
)
```

**Production:**

```python
config = MonitoringConfig(
    service_name="your-service",
    environment="production",
    log_level=LogLevel.INFO,
    use_cloudwatch_logs=True,
    use_cloudwatch_metrics=True,
    use_xray=True
)
```

## Monitoring Components

### Structured Logger

```python
from packages.shared.monitoring import get_logger, LogLevel, EventType

logger = get_logger()

# Basic logging
logger.info("Operation completed", extra={"duration_ms": 150})

# Error logging with exception
try:
    risky_operation()
except Exception as e:
    logger.error("Operation failed", error=e, extra={"context": "important"})

# Business events
logger.business_event(
    event_type=EventType.USER_ACTION,
    entity_type="user",
    entity_id="user_123",
    action="profile_updated",
    metadata={"fields": ["email", "preferences"]}
)
```

### Performance Monitoring

```python
from packages.shared.monitoring import performance_monitor

@performance_monitor("database_operation")
async def get_user_data(user_id: str):
    # Automatic performance tracking
    return await db.get_user(user_id)

# Context manager for manual tracking
with logger.operation_context("complex_operation") as ctx:
    ctx.info("Starting phase 1")
    await phase_1()

    ctx.info("Starting phase 2")
    await phase_2()
    # Automatic duration tracking
```

### Metrics Collection

```python
from packages.shared.monitoring import get_metrics, get_business_metrics

metrics = get_metrics()
business_metrics = get_business_metrics()

# Counters
counter = metrics.counter("api_requests_total")
counter.increment(tags={"endpoint": "/api/users", "method": "GET"})

# Gauges
gauge = metrics.gauge("active_users")
gauge.set(150, tags={"service": "api"})

# Histograms for response times
histogram = metrics.histogram("response_time_ms")
histogram.observe(250.5, tags={"endpoint": "/api/nutrition"})

# Business metrics
business_metrics.track_user_action("meal_analyzed", "user_123", success=True)
business_metrics.track_api_request("/api/nutrition", "POST", 200, 150.0)
```

### Distributed Tracing

```python
from packages.shared.monitoring import get_tracer, trace_operation

tracer = get_tracer()

# Decorator-based tracing
@trace_operation("user_lookup")
async def get_user(user_id: str):
    return await db.get_user(user_id)

# Manual span management
with tracer.trace("complex_operation") as span:
    span.add_tag("user_id", "123")
    span.add_log("Starting data processing")

    result = await process_data()

    span.add_tag("result_count", len(result))
    return result
```

### Health Monitoring

```python
from packages.shared.monitoring import get_health_monitor, DatabaseHealthCheck

health_monitor = get_health_monitor()

# Add custom health checks
db_check = DatabaseHealthCheck("database", connection_factory)
health_monitor.add_check(db_check)

# Check health
health_status = await health_monitor.check_health()
print(f"Service health: {health_status.status}")
```

## Log Output Examples

### Structured JSON Log Entry

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "message": "Request completed: POST /api/v1/nutrition/analyze - 200",
  "context": {
    "correlation_id": "req_12345",
    "user_id": "user_789",
    "request_id": "api_67890",
    "service_name": "ai-nutritionist-api",
    "operation": "POST /api/v1/nutrition/analyze"
  },
  "business_event": {
    "event_type": "user_action",
    "entity_type": "nutrition_analysis",
    "entity_id": "analysis_456",
    "action": "completed",
    "metadata": {
      "total_calories": 450,
      "food_items_count": 3,
      "recommendations_count": 2
    }
  },
  "performance": {
    "duration_ms": 150.5,
    "operation_count": 1
  },
  "extra": {
    "response": {
      "status_code": 200,
      "duration_ms": 150.5
    },
    "request": {
      "method": "POST",
      "path": "/api/v1/nutrition/analyze",
      "user_agent": "AI-Nutritionist-App/1.0"
    }
  }
}
```

### Error Log Entry

```json
{
  "timestamp": "2024-01-15T10:31:15.456Z",
  "level": "ERROR",
  "message": "Database query failed",
  "context": {
    "correlation_id": "req_12346",
    "service_name": "ai-nutritionist-api",
    "operation": "get_user_by_id"
  },
  "error": {
    "type": "ConnectionError",
    "message": "Unable to connect to database",
    "traceback": "Traceback (most recent call last)..."
  },
  "business_event": {
    "event_type": "error_event",
    "entity_type": "database",
    "action": "query_failed",
    "metadata": {
      "table": "users",
      "operation": "select",
      "user_id": "user_789"
    }
  },
  "performance": {
    "duration_ms": 5000.0
  }
}
```

## Privacy and Compliance

### PII Masking

The framework automatically masks PII data:

```python
# Input
log_data = {
    "user_email": "john.doe@example.com",
    "phone": "555-123-4567",
    "message": "User john.doe@example.com updated profile"
}

# Logged output (PII masked)
{
    "user_email": "[MASKED_EMAIL]",
    "phone": "[MASKED_PHONE]",
    "message": "User [MASKED_EMAIL] updated profile"
}
```

### GDPR Compliance

- **Audit Logging**: All data access and modifications are logged
- **Data Retention**: Configurable log retention policies
- **Right to be Forgotten**: Support for removing user data from logs
- **Consent Tracking**: Log user consent and preferences

### Security Logging

```python
# Authentication failures
logger.business_event(
    event_type=EventType.SECURITY_EVENT,
    entity_type="authentication",
    action="failed_login",
    metadata={
        "ip_address": "192.168.1.1",
        "user_agent": "Browser/1.0",
        "reason": "invalid_credentials"
    },
    level=LogLevel.WARN
)

# Unauthorized access attempts
logger.business_event(
    event_type=EventType.SECURITY_EVENT,
    entity_type="authorization",
    action="unauthorized_access",
    metadata={
        "user_id": "user_123",
        "resource": "/admin/users",
        "required_role": "admin"
    },
    level=LogLevel.ERROR
)
```

## CloudWatch Integration

### Log Groups Structure

```
/ai-nutritionist/api/application      - Application logs (14 days)
/ai-nutritionist/api/error           - Error logs (90 days)
/ai-nutritionist/api/audit           - Audit logs (365 days)
/ai-nutritionist/api/security        - Security logs (90 days)
/aws/lambda/ai-nutritionist-api      - Lambda logs (30 days)
```

### Useful CloudWatch Queries

**Error Analysis:**

```sql
fields @timestamp, level, message, error.type
| filter level = "ERROR"
| stats count() by error.type
| sort count desc
```

**API Performance:**

```sql
fields @timestamp, context.operation, performance.duration_ms
| filter context.operation like /api/
| stats avg(performance.duration_ms), max(performance.duration_ms) by context.operation
```

**User Activity:**

```sql
fields @timestamp, business_event.action, context.user_id
| filter business_event.event_type = "user_action"
| stats count() by business_event.action
```

### Metrics and Alarms

- **api_requests_total**: Total API requests by endpoint and status
- **api_response_time_ms**: API response time percentiles
- **api_errors_total**: API errors by type and endpoint
- **db_operations_total**: Database operations by table and type
- **external_api_calls_total**: External API calls by service
- **business_events_total**: Business events by type and action

## Best Practices

### 1. Correlation IDs

Always use correlation IDs to track requests across services:

```python
# Extract from headers or generate
correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
logger.context.correlation_id = correlation_id

# Pass to downstream services
headers = tracer.inject_context({"X-Correlation-ID": correlation_id})
```

### 2. Structured Data

Use structured data in log messages:

```python
# Good
logger.info(
    "User updated profile",
    extra={
        "user_id": "user_123",
        "fields_changed": ["email", "preferences"],
        "timestamp": datetime.utcnow().isoformat()
    }
)

# Avoid
logger.info(f"User user_123 updated email and preferences at {timestamp}")
```

### 3. Log Levels

Use appropriate log levels:

- **DEBUG**: Detailed development information
- **INFO**: General application flow and business events
- **WARN**: Degraded performance or recoverable errors
- **ERROR**: Application errors that need attention
- **FATAL**: Critical system failures

### 4. Performance Considerations

- Use async logging to avoid blocking
- Buffer logs for batch sending to CloudWatch
- Set appropriate log levels for production
- Use sampling for high-volume traces

### 5. Security

- Never log sensitive data (passwords, tokens, etc.)
- Use PII masking for user data
- Implement proper access controls for logs
- Rotate log access credentials regularly

## Troubleshooting

### Common Issues

1. **CloudWatch Permissions**: Ensure IAM roles have CloudWatch permissions
2. **Log Group Creation**: Check if log groups exist and have correct retention
3. **Metric Filters**: Verify filter patterns match log format
4. **X-Ray Setup**: Ensure X-Ray daemon is running for local development

### Debug Mode

Enable debug logging:

```python
config = MonitoringConfig(
    log_level=LogLevel.DEBUG,
    use_cloudwatch_logs=False  # Use console for debugging
)
```

## Running Examples

Each example can be run independently:

```bash
# API layer example
python examples/api_logging_example.py

# Domain service example
python examples/domain_service_logging_example.py

# Infrastructure layer example
python examples/infrastructure_logging_example.py

# CloudWatch integration
python examples/cloudwatch_integration_example.py
```

## Integration with Existing Services

To integrate with existing services:

1. Add monitoring setup to service initialization
2. Replace existing logging with structured logger
3. Add performance monitoring to critical operations
4. Implement health checks for dependencies
5. Setup CloudWatch integration for production

```python
# Service initialization
from packages.shared.monitoring.setup import setup_service_monitoring

def initialize_service():
    monitoring = setup_service_monitoring("your-service")

    # Add health checks
    monitoring.add_database_health_check("database", db_connection_factory)
    monitoring.add_external_api_health_check("external_api", "https://api.example.com/health")

    return monitoring
```
