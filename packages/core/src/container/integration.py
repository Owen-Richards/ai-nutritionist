"""
DI Integration Guide
===================

Shows how to integrate the DI container with existing services.
"""

from typing import Optional, Dict, Any
import boto3

from packages.core.src.container import (
    Container, injectable, singleton, scoped,
    get_container, configure_container
)
from packages.core.src.container.lifetime import ServiceLifetime
from packages.core.src.container.configuration import (
    DatabaseConfig, AIConfig, MessagingConfig,
    get_application_config
)


# Example: Converting existing service to use DI
# Before: Manual dependency management
class NutritionServiceOld:
    """Old nutrition service with manual dependencies."""
    
    def __init__(self):
        # Manual dependency creation - ANTI-PATTERN
        import boto3
        self.dynamodb = boto3.resource('dynamodb')
        self.ai_client = boto3.client('bedrock-runtime')
        self.table_name = 'ai-nutritionist-users'
    
    def get_nutrition_advice(self, user_id: str, food_item: str) -> str:
        # Business logic with tightly coupled dependencies
        return f"Nutrition advice for {food_item}"


# After: DI-enabled service
@injectable()
class NutritionServiceNew:
    """New nutrition service with dependency injection."""
    
    def __init__(
        self,
        database_config: DatabaseConfig,
        ai_config: AIConfig,
        dynamodb_resource,  # Injected AWS resource
        bedrock_client      # Injected AI client
    ):
        self.database_config = database_config
        self.ai_config = ai_config
        self.dynamodb = dynamodb_resource
        self.bedrock_client = bedrock_client
    
    def get_nutrition_advice(self, user_id: str, food_item: str) -> str:
        # Business logic with injected dependencies
        return f"AI-powered nutrition advice for {food_item} using {self.ai_config.model_name}"


# Example: Service Factory Pattern
class ServiceFactory:
    """Factory for creating services with dependencies."""
    
    def __init__(self, container: Container):
        self.container = container
    
    def create_nutrition_service(self) -> NutritionServiceNew:
        """Create nutrition service with all dependencies."""
        return self.container.resolve(NutritionServiceNew)
    
    def create_user_service(self) -> 'UserServiceDI':
        """Create user service with all dependencies."""
        return self.container.resolve(UserServiceDI)


# Example: Adapter Pattern for Legacy Services
@injectable()
class LegacyServiceAdapter:
    """Adapter for legacy services that can't be modified."""
    
    def __init__(self, database_config: DatabaseConfig):
        self.database_config = database_config
        # Initialize legacy service with configuration
        self.legacy_service = self._create_legacy_service()
    
    def _create_legacy_service(self):
        """Create legacy service with proper configuration."""
        # This would be your existing service
        return "legacy_service_instance"
    
    def get_data(self, key: str) -> Any:
        """Wrapper method that uses legacy service."""
        return f"legacy_data_for_{key}"


# Example: Complex Service with Multiple Dependencies
@scoped
class UserServiceDI:
    """User service with multiple injected dependencies."""
    
    def __init__(
        self,
        database_config: DatabaseConfig,
        messaging_config: MessagingConfig,
        nutrition_service: NutritionServiceNew,
        cache_service: Optional['CacheServiceDI'] = None
    ):
        self.database_config = database_config
        self.messaging_config = messaging_config
        self.nutrition_service = nutrition_service
        self.cache_service = cache_service
    
    def create_user_profile(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create user profile with nutrition recommendations."""
        # Use injected services
        nutrition_advice = self.nutrition_service.get_nutrition_advice(
            user_data['id'], 
            user_data.get('favorite_food', 'apple')
        )
        
        user_data['nutrition_advice'] = nutrition_advice
        
        # Cache if available
        if self.cache_service:
            self.cache_service.set(f"user_{user_data['id']}", user_data)
        
        return user_data


@singleton
class CacheServiceDI:
    """Singleton cache service."""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
    
    def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)
    
    def set(self, key: str, value: Any) -> None:
        self._cache[key] = value


# Example: Handler with DI
class DIEnabledHandler:
    """Lambda handler that uses DI container."""
    
    def __init__(self):
        self.container = self._setup_container()
    
    def _setup_container(self) -> Container:
        """Setup and configure the DI container."""
        container = configure_container()
        
        # Register configuration
        config = get_application_config()
        container.register_instance(DatabaseConfig, config.database)
        container.register_instance(AIConfig, config.ai)
        container.register_instance(MessagingConfig, config.messaging)
        
        # Register AWS services
        container.register_factory(
            'dynamodb_resource',
            lambda: boto3.resource('dynamodb'),
            ServiceLifetime.SINGLETON
        )
        
        container.register_factory(
            'bedrock_client',
            lambda: boto3.client('bedrock-runtime'),
            ServiceLifetime.SINGLETON
        )
        
        # Register application services
        container.register_scoped(NutritionServiceNew)
        container.register_scoped(UserServiceDI)
        container.register_singleton(CacheServiceDI)
        container.register_transient(LegacyServiceAdapter)
        
        return container
    
    def handle_nutrition_request(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle nutrition advice request."""
        try:
            with self.container.create_scope():
                # Resolve services
                nutrition_service = self.container.resolve(NutritionServiceNew)
                
                # Process request
                user_id = event.get('user_id')
                food_item = event.get('food_item')
                
                advice = nutrition_service.get_nutrition_advice(user_id, food_item)
                
                return {
                    'statusCode': 200,
                    'body': {'advice': advice}
                }
        
        except Exception as e:
            return {
                'statusCode': 500,
                'body': {'error': str(e)}
            }
    
    def handle_user_creation(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle user creation request."""
        try:
            with self.container.create_scope():
                # Resolve services
                user_service = self.container.resolve(UserServiceDI)
                
                # Process request
                user_data = event.get('user_data', {})
                result = user_service.create_user_profile(user_data)
                
                return {
                    'statusCode': 200,
                    'body': result
                }
        
        except Exception as e:
            return {
                'statusCode': 500,
                'body': {'error': str(e)}
            }


# Example: Testing with DI
class MockNutritionService(NutritionServiceNew):
    """Mock nutrition service for testing."""
    
    def __init__(self):
        # No dependencies needed for testing
        pass
    
    def get_nutrition_advice(self, user_id: str, food_item: str) -> str:
        return f"Mock advice for {food_item}"


def setup_test_container() -> Container:
    """Setup container for testing with mocks."""
    container = Container()
    
    # Register mock services
    container.register_instance(NutritionServiceNew, MockNutritionService())
    container.register_singleton(CacheServiceDI)
    
    # Register test configuration
    test_db_config = DatabaseConfig(
        table_name="test-table",
        region="us-east-1"
    )
    container.register_instance(DatabaseConfig, test_db_config)
    
    test_messaging_config = MessagingConfig(
        aws_region="us-east-1",
        sender_id="TEST"
    )
    container.register_instance(MessagingConfig, test_messaging_config)
    
    container.register_scoped(UserServiceDI)
    
    return container


# Migration Guide Functions
def migrate_existing_service_to_di():
    """Guide for migrating existing services to DI."""
    steps = [
        "1. Identify dependencies in constructor or init method",
        "2. Add type annotations for all dependencies", 
        "3. Add @injectable() decorator to the class",
        "4. Remove manual dependency creation",
        "5. Register service and dependencies in container",
        "6. Update calling code to resolve from container",
        "7. Add tests with mock dependencies"
    ]
    
    print("Migration Steps:")
    for step in steps:
        print(f"  {step}")


def run_integration_examples():
    """Run integration examples."""
    print("=== DI Integration Examples ===\n")
    
    # Example 1: Basic service conversion
    print("1. Service Conversion Example:")
    handler = DIEnabledHandler()
    
    # Test nutrition request
    nutrition_event = {
        'user_id': 'user123',
        'food_item': 'apple'
    }
    
    result = handler.handle_nutrition_request(nutrition_event)
    print(f"Nutrition result: {result}")
    print()
    
    # Example 2: User creation with dependencies
    print("2. Complex Service Example:")
    user_event = {
        'user_data': {
            'id': 'user456',
            'name': 'John Doe',
            'favorite_food': 'banana'
        }
    }
    
    result = handler.handle_user_creation(user_event)
    print(f"User creation result: {result}")
    print()
    
    # Example 3: Testing with mocks
    print("3. Testing with Mocks:")
    test_container = setup_test_container()
    
    with test_container.create_scope():
        user_service = test_container.resolve(UserServiceDI)
        test_user = {
            'id': 'test123',
            'name': 'Test User',
            'favorite_food': 'carrot'
        }
        
        result = user_service.create_user_profile(test_user)
        print(f"Test result: {result}")
    print()
    
    # Example 4: Service validation
    print("4. Service Validation:")
    issues = handler.container.validate_services()
    if issues:
        print("Issues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("All services valid!")
    print()
    
    # Example 5: Migration guide
    print("5. Migration Guide:")
    migrate_existing_service_to_di()
    
    print("\n=== Integration Examples Complete ===")


if __name__ == "__main__":
    run_integration_examples()
