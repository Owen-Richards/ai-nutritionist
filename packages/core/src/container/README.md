# Dependency Injection Container System

A comprehensive, enterprise-grade dependency injection container for the AI Nutritionist monorepo.

## Features

- **Service Registration & Resolution**: Register services with different lifetime strategies
- **Lifetime Management**: Singleton, Scoped, and Transient service lifetimes
- **Automatic Injection**: Constructor and property injection with type annotation support
- **Configuration Management**: Environment-specific configs, secrets, and feature flags
- **Provider Pattern**: Extensible providers for external services and complex object creation
- **Circular Dependency Detection**: Prevents and reports circular dependency issues
- **Thread Safety**: Thread-safe operations with proper locking mechanisms
- **Service Validation**: Comprehensive validation of service registrations

## Quick Start

### 1. Basic Service Registration

```python
from packages.core.src.container import Container, injectable, singleton

@injectable()
class EmailService:
    def send_email(self, to: str, subject: str, body: str) -> bool:
        print(f"Sending email to {to}: {subject}")
        return True

@injectable()
class NotificationService:
    def __init__(self, email_service: EmailService):
        self.email_service = email_service

    def send_notification(self, user_id: str, message: str) -> bool:
        return self.email_service.send_email(
            f"user_{user_id}@example.com",
            "Notification",
            message
        )

# Setup container
container = Container()
container.register_transient(EmailService)
container.register_transient(NotificationService)

# Resolve service with automatic dependency injection
notification_service = container.resolve(NotificationService)
notification_service.send_notification("123", "Hello World!")
```

### 2. Configuration and Secrets

```python
from packages.core.src.container.configuration import ApplicationConfig, DatabaseConfig

# Automatic configuration from environment
config = ApplicationConfig.from_environment()

# Register configuration in container
container.register_instance(DatabaseConfig, config.database)

@injectable()
class UserRepository:
    def __init__(self, database_config: DatabaseConfig):
        self.config = database_config
        print(f"Connected to: {database_config.table_name}")
```

### 3. Service Lifetimes

```python
# Singleton - One instance per container
@singleton
class CacheService:
    def __init__(self):
        self._cache = {}

# Scoped - One instance per scope
@scoped
class RequestContextService:
    def __init__(self):
        self.request_id = None

# Transient - New instance every time (default)
@injectable()
class EmailService:
    def __init__(self):
        pass
```

### 4. Scoped Services

```python
with container.create_scope():
    # All scoped services share the same instances within this scope
    service1 = container.resolve(RequestContextService)
    service2 = container.resolve(RequestContextService)
    assert service1 is service2  # Same instance
# Scope disposed, scoped instances cleaned up
```

## Architecture

### Core Components

1. **Container**: Main DI container with service resolution
2. **ServiceRegistry**: Manages service descriptors and dependency metadata
3. **LifetimeManagers**: Handle different service lifetime strategies
4. **ServiceProviders**: Extensible providers for external services
5. **Configuration System**: Environment-aware configuration management

### Service Lifetimes

- **Singleton**: One instance per container (thread-safe)
- **Scoped**: One instance per scope (useful for request/operation context)
- **Transient**: New instance every time (stateless services)

### Dependency Resolution

1. Check if service is registered
2. Analyze constructor dependencies
3. Recursively resolve dependencies
4. Create instance using appropriate lifetime manager
5. Return configured instance

## Configuration Management

### Environment Variables

```bash
# Database Configuration
AI_NUTRITIONIST_TABLE_NAME=ai-nutritionist-users
AI_NUTRITIONIST_REGION=us-east-1

# AI Configuration
AI_NUTRITIONIST_MODEL_NAME=anthropic.claude-3-sonnet-20240229-v1:0
AI_NUTRITIONIST_MAX_TOKENS=4000

# Feature Flags
AI_NUTRITIONIST_EXPERIMENTAL_FEATURES=false
AI_NUTRITIONIST_ADVANCED_ANALYTICS=true
```

### AWS Parameter Store

```
/ai-nutritionist/database/table_name
/ai-nutritionist/ai/model_name
/ai-nutritionist/features/experimental_features
```

### Configuration Classes

```python
@dataclass
class DatabaseConfig:
    table_name: str = "ai-nutritionist-users"
    region: str = "us-east-1"
    endpoint_url: Optional[str] = None

@dataclass
class AIConfig:
    model_name: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    region: str = "us-east-1"
    max_tokens: int = 4000
    temperature: float = 0.7
```

## Service Registration

### Automatic Registration

```python
from packages.core.src.container.registration import create_configured_container

# Creates container with all application services registered
container = create_configured_container()
```

### Manual Registration

```python
# Register service types
container.register_singleton(CacheService)
container.register_scoped(UserService)
container.register_transient(EmailService)

# Register interfaces to implementations
container.register_scoped(IUserRepository, DatabaseUserRepository)

# Register instances
container.register_instance(DatabaseConfig, config.database)

# Register factories
container.register_factory(
    'database_connection',
    lambda config: create_connection(config),
    ServiceLifetime.SINGLETON
)
```

## Integration with Existing Services

### Before (Manual Dependencies)

```python
class NutritionService:
    def __init__(self):
        # Manual dependency creation - ANTI-PATTERN
        self.dynamodb = boto3.resource('dynamodb')
        self.ai_client = boto3.client('bedrock-runtime')
        self.table_name = 'ai-nutritionist-users'
```

### After (Dependency Injection)

```python
@injectable()
class NutritionService:
    def __init__(
        self,
        database_config: DatabaseConfig,
        ai_config: AIConfig,
        dynamodb_resource,
        bedrock_client
    ):
        self.database_config = database_config
        self.ai_config = ai_config
        self.dynamodb = dynamodb_resource
        self.bedrock_client = bedrock_client
```

## Error Handling

### Circular Dependency Detection

```python
# Automatically detects and prevents circular dependencies
try:
    service = container.resolve(MyService)
except CircularDependencyException as e:
    print(f"Circular dependency: {e.dependency_chain}")
```

### Service Validation

```python
# Validate all registered services
issues = container.validate_services()
for issue in issues:
    print(f"Validation issue: {issue}")
```

## Testing

### Mock Services

```python
class MockEmailService(EmailService):
    def send_email(self, to: str, subject: str, body: str) -> bool:
        return True

# Setup test container with mocks
test_container = Container()
test_container.register_instance(EmailService, MockEmailService())
```

### Test Scopes

```python
def test_user_service():
    with test_container.create_scope():
        user_service = test_container.resolve(UserService)
        # Test with isolated scope
```

## Performance Considerations

- **Singleton Services**: Cached after first resolution
- **Constructor Analysis**: Cached using reflection
- **Thread Safety**: All operations are thread-safe
- **Memory Management**: Proper disposal of scoped services

## Migration Guide

1. **Identify Dependencies**: List all manual dependencies in constructors
2. **Add Type Annotations**: Ensure all dependencies have type hints
3. **Add Decorators**: Use `@injectable()`, `@singleton`, etc.
4. **Remove Manual Creation**: Delete manual dependency instantiation
5. **Register Services**: Add service registrations to container
6. **Update Calling Code**: Resolve services from container
7. **Add Tests**: Create tests with mock dependencies

## Best Practices

1. **Use Interfaces**: Register interfaces mapped to implementations
2. **Minimize Dependencies**: Keep constructor parameters focused
3. **Avoid Service Locator**: Don't pass container to services
4. **Configuration First**: Use configuration objects instead of raw values
5. **Validate Early**: Run container validation during startup
6. **Scope Appropriately**: Choose correct lifetime for each service
7. **Test with Mocks**: Create testable services with mock dependencies

## Examples

See the following files for complete examples:

- `examples.py` - Basic usage examples
- `integration.py` - Integration with existing services
- `registration.py` - Service registration patterns

## Error Reference

- `ServiceNotRegisteredException`: Service type not registered
- `CircularDependencyException`: Circular dependency detected
- `ConfigurationException`: Configuration loading failed
- `ScopeException`: Scope operation failed
- `FactoryException`: Factory function failed

## Environment Setup

```bash
# Required environment variables
export ENVIRONMENT=development
export AWS_REGION=us-east-1
export DYNAMODB_TABLE_NAME=ai-nutritionist-users

# Optional feature flags
export AI_NUTRITIONIST_EXPERIMENTAL_FEATURES=false
export AI_NUTRITIONIST_ADVANCED_ANALYTICS=true
```
