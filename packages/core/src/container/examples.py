"""
DI Container Examples
====================

Examples showing how to use the dependency injection container.
"""

from typing import Optional
from abc import ABC, abstractmethod

from packages.core.src.container import (
    Container, injectable, singleton, scoped, transient,
    get_container, configure_container
)
from packages.core.src.container.configuration import (
    ApplicationConfig, DatabaseConfig, AIConfig,
    get_application_config
)


# Example 1: Basic Service Registration and Resolution
@injectable()
class EmailService:
    """Example email service."""
    
    def send_email(self, to: str, subject: str, body: str) -> bool:
        print(f"Sending email to {to}: {subject}")
        return True


@injectable()
class NotificationService:
    """Example notification service with dependency injection."""
    
    def __init__(self, email_service: EmailService):
        self.email_service = email_service
    
    def send_notification(self, user_id: str, message: str) -> bool:
        # Use injected email service
        return self.email_service.send_email(
            f"user_{user_id}@example.com",
            "Notification",
            message
        )


# Example 2: Interface-based Injection
class IUserRepository(ABC):
    """Abstract user repository interface."""
    
    @abstractmethod
    def get_user(self, user_id: str) -> Optional[dict]:
        pass
    
    @abstractmethod
    def save_user(self, user: dict) -> bool:
        pass


@injectable()
class DatabaseUserRepository(IUserRepository):
    """Database implementation of user repository."""
    
    def __init__(self, database_config: DatabaseConfig):
        self.database_config = database_config
        print(f"Connected to database: {database_config.table_name}")
    
    def get_user(self, user_id: str) -> Optional[dict]:
        print(f"Getting user {user_id} from database")
        return {"id": user_id, "name": "John Doe"}
    
    def save_user(self, user: dict) -> bool:
        print(f"Saving user to database: {user}")
        return True


@injectable()
class UserService:
    """User service with repository injection."""
    
    def __init__(self, user_repository: IUserRepository):
        self.user_repository = user_repository
    
    def create_user(self, user_data: dict) -> bool:
        # Business logic here
        user_data['created_at'] = '2025-01-01'
        return self.user_repository.save_user(user_data)


# Example 3: Singleton Services
@singleton
class CacheService:
    """Singleton cache service."""
    
    def __init__(self):
        self._cache = {}
        print("Cache service initialized")
    
    def get(self, key: str) -> Optional[str]:
        return self._cache.get(key)
    
    def set(self, key: str, value: str) -> None:
        self._cache[key] = value


# Example 4: Factory Pattern with DI
@injectable()
class DatabaseConnectionFactory:
    """Factory for creating database connections."""
    
    def __init__(self, database_config: DatabaseConfig):
        self.database_config = database_config
    
    def create_connection(self):
        print(f"Creating database connection to {self.database_config.table_name}")
        return f"connection_{self.database_config.table_name}"


@injectable()
class ComplexService:
    """Service using factory pattern."""
    
    def __init__(self, connection_factory: DatabaseConnectionFactory, cache_service: CacheService):
        self.connection_factory = connection_factory
        self.cache_service = cache_service
        self.connection = None
    
    def connect(self):
        if self.connection is None:
            self.connection = self.connection_factory.create_connection()
        return self.connection
    
    def get_data(self, key: str) -> str:
        # Check cache first
        cached_data = self.cache_service.get(key)
        if cached_data:
            return cached_data
        
        # Get from database
        self.connect()
        data = f"data_for_{key}"
        self.cache_service.set(key, data)
        return data


# Example 5: Configuration Injection
@injectable()
class AIServiceExample:
    """AI service with configuration injection."""
    
    def __init__(self, ai_config: AIConfig):
        self.ai_config = ai_config
        print(f"AI Service initialized with model: {ai_config.model_name}")
    
    def generate_response(self, prompt: str) -> str:
        print(f"Generating response with {self.ai_config.model_name}")
        return f"AI response to: {prompt}"


# Example 6: Scoped Services
@scoped
class RequestContextService:
    """Scoped service for request-specific data."""
    
    def __init__(self):
        self.request_id = None
        self.user_id = None
        print("Request context created")
    
    def set_context(self, request_id: str, user_id: str):
        self.request_id = request_id
        self.user_id = user_id
    
    def get_context(self) -> dict:
        return {
            'request_id': self.request_id,
            'user_id': self.user_id
        }


@injectable()
class BusinessService:
    """Business service using scoped context."""
    
    def __init__(self, context: RequestContextService, user_service: UserService):
        self.context = context
        self.user_service = user_service
    
    def process_request(self, data: dict) -> dict:
        context = self.context.get_context()
        print(f"Processing request {context['request_id']} for user {context['user_id']}")
        
        # Use other services
        result = self.user_service.create_user(data)
        return {'success': result, 'context': context}


def setup_container_examples() -> Container:
    """Setup container with example services."""
    container = configure_container()
    
    # Register interfaces to implementations
    container.register_scoped(IUserRepository, DatabaseUserRepository)
    
    # Register services (decorators handle automatic registration)
    container.register_transient(EmailService)
    container.register_transient(NotificationService)
    container.register_scoped(UserService)
    container.register_singleton(CacheService)
    container.register_transient(DatabaseConnectionFactory)
    container.register_transient(ComplexService)
    container.register_transient(AIServiceExample)
    container.register_scoped(RequestContextService)
    container.register_transient(BusinessService)
    
    # Register configuration
    app_config = get_application_config()
    container.register_instance(ApplicationConfig, app_config)
    container.register_instance(DatabaseConfig, app_config.database)
    container.register_instance(AIConfig, app_config.ai)
    
    return container


def run_examples():
    """Run DI container examples."""
    print("=== Dependency Injection Container Examples ===\n")
    
    # Setup container
    container = setup_container_examples()
    
    # Example 1: Basic service resolution
    print("1. Basic Service Resolution:")
    notification_service = container.resolve(NotificationService)
    notification_service.send_notification("123", "Hello World!")
    print()
    
    # Example 2: Interface-based injection
    print("2. Interface-based Injection:")
    user_service = container.resolve(UserService)
    user_service.create_user({"name": "Jane Doe", "email": "jane@example.com"})
    print()
    
    # Example 3: Singleton behavior
    print("3. Singleton Behavior:")
    cache1 = container.resolve(CacheService)
    cache2 = container.resolve(CacheService)
    print(f"Same instance: {cache1 is cache2}")
    cache1.set("key1", "value1")
    print(f"Cache2 has key1: {cache2.get('key1')}")
    print()
    
    # Example 4: Factory pattern
    print("4. Factory Pattern:")
    complex_service = container.resolve(ComplexService)
    data = complex_service.get_data("test_key")
    print(f"Retrieved data: {data}")
    print()
    
    # Example 5: Configuration injection
    print("5. Configuration Injection:")
    ai_service = container.resolve(AIServiceExample)
    response = ai_service.generate_response("What is dependency injection?")
    print(f"AI Response: {response}")
    print()
    
    # Example 6: Scoped services
    print("6. Scoped Services:")
    with container.create_scope():
        context = container.resolve(RequestContextService)
        context.set_context("req_123", "user_456")
        
        business_service = container.resolve(BusinessService)
        result = business_service.process_request({"name": "Test User"})
        print(f"Business result: {result}")
    print()
    
    # Example 7: Service validation
    print("7. Service Validation:")
    issues = container.validate_services()
    if issues:
        print("Validation issues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("All services validated successfully!")
    print()
    
    # Example 8: Service information
    print("8. Service Information:")
    service_info = container.get_service_info()
    for service_name, info in service_info.items():
        print(f"{service_name}: {info['lifetime']} ({len(info['dependencies'])} dependencies)")
    
    print("\n=== Examples Complete ===")


if __name__ == "__main__":
    run_examples()
