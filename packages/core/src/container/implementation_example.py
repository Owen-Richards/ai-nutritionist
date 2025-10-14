"""
DI Container Implementation Example
==================================

Complete example showing how to implement dependency injection
throughout the AI Nutritionist monorepo.
"""

from typing import Optional, Dict, Any, List
import os
from dataclasses import dataclass
import boto3

from packages.core.src.container import (
    Container, injectable, singleton, scoped, transient,
    get_container, configure_container
)
from packages.core.src.container.configuration import (
    ApplicationConfig, DatabaseConfig, AIConfig, MessagingConfig,
    get_application_config, get_config_manager
)


# =============================================================================
# 1. DOMAIN SERVICES WITH DI
# =============================================================================

@dataclass
class NutritionProfile:
    """Nutrition profile value object."""
    user_id: str
    daily_calories: int
    protein_goal: float
    carb_goal: float
    fat_goal: float


@injectable()
class NutritionCalculatorService:
    """Core nutrition calculation service."""
    
    def __init__(self, ai_config: AIConfig):
        self.ai_config = ai_config
        self.multipliers = {
            'sedentary': 1.2,
            'light': 1.375,
            'moderate': 1.55,
            'active': 1.725,
            'very_active': 1.9
        }
    
    def calculate_bmr(self, weight: float, height: float, age: int, gender: str) -> float:
        """Calculate Basal Metabolic Rate."""
        if gender.lower() == 'male':
            return 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
        else:
            return 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)
    
    def calculate_daily_calories(self, bmr: float, activity_level: str) -> int:
        """Calculate daily calorie needs."""
        multiplier = self.multipliers.get(activity_level, 1.2)
        return int(bmr * multiplier)


@injectable()
class MealPlanGeneratorService:
    """AI-powered meal plan generation."""
    
    def __init__(
        self,
        nutrition_calculator: NutritionCalculatorService,
        ai_client,  # Will be injected
        database_config: DatabaseConfig
    ):
        self.nutrition_calculator = nutrition_calculator
        self.ai_client = ai_client
        self.database_config = database_config
    
    def generate_meal_plan(
        self, 
        user_profile: NutritionProfile, 
        dietary_restrictions: List[str] = None
    ) -> Dict[str, Any]:
        """Generate personalized meal plan."""
        return {
            'breakfast': 'AI-generated breakfast',
            'lunch': 'AI-generated lunch',
            'dinner': 'AI-generated dinner',
            'calories': user_profile.daily_calories,
            'restrictions': dietary_restrictions or []
        }


# =============================================================================
# 2. INFRASTRUCTURE SERVICES WITH DI
# =============================================================================

@singleton
class CacheService:
    """Redis-based caching service."""
    
    def __init__(self, cache_config: dict):
        self.cache_config = cache_config
        self.redis_client = self._create_redis_client()
    
    def _create_redis_client(self):
        """Create Redis client from configuration."""
        # In real implementation, would use redis-py
        return f"redis_client_with_url_{self.cache_config.get('redis_url', 'localhost:6379')}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        return f"cached_value_for_{key}"
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache."""
        return True


@singleton
class MetricsService:
    """Application metrics and monitoring."""
    
    def __init__(self, monitoring_config: dict):
        self.monitoring_config = monitoring_config
        self.enabled = monitoring_config.get('metrics_enabled', True)
    
    def increment_counter(self, metric_name: str, tags: Dict[str, str] = None) -> None:
        """Increment a counter metric."""
        if self.enabled:
            print(f"Incrementing metric: {metric_name} with tags: {tags}")
    
    def record_timing(self, metric_name: str, duration_ms: float, tags: Dict[str, str] = None) -> None:
        """Record timing metric."""
        if self.enabled:
            print(f"Recording timing: {metric_name} = {duration_ms}ms with tags: {tags}")


@scoped
class MessageService:
    """AWS messaging service."""
    
    def __init__(
        self,
        messaging_config: MessagingConfig,
        sns_client,  # Injected AWS SNS client
        cache_service: CacheService,
        metrics_service: MetricsService
    ):
        self.messaging_config = messaging_config
        self.sns_client = sns_client
        self.cache_service = cache_service
        self.metrics_service = metrics_service
    
    def send_sms(self, phone_number: str, message: str) -> bool:
        """Send SMS message."""
        self.metrics_service.increment_counter(
            'sms_sent',
            {'region': self.messaging_config.aws_region}
        )
        return True
    
    def send_nutrition_reminder(self, user_id: str, message: str) -> bool:
        """Send nutrition reminder to user."""
        # Get user phone from cache or database
        phone = self.cache_service.get(f"user_phone_{user_id}")
        if phone:
            return self.send_sms(phone, message)
        return False


# =============================================================================
# 3. REPOSITORY PATTERN WITH DI
# =============================================================================

@injectable()
class UserRepositoryInterface:
    """Abstract user repository interface."""
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        raise NotImplementedError
    
    def save_user(self, user: Dict[str, Any]) -> bool:
        """Save user."""
        raise NotImplementedError


@injectable()
class DynamoDBUserRepository(UserRepositoryInterface):
    """DynamoDB implementation of user repository."""
    
    def __init__(
        self,
        database_config: DatabaseConfig,
        dynamodb_resource,  # Injected DynamoDB resource
        cache_service: CacheService,
        metrics_service: MetricsService
    ):
        self.database_config = database_config
        self.dynamodb = dynamodb_resource
        self.cache_service = cache_service
        self.metrics_service = metrics_service
        self.table = self._get_table()
    
    def _get_table(self):
        """Get DynamoDB table."""
        return f"table_{self.database_config.table_name}"
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID with caching."""
        cache_key = f"user_{user_id}"
        
        # Try cache first
        cached_user = self.cache_service.get(cache_key)
        if cached_user:
            self.metrics_service.increment_counter('user_cache_hit')
            return cached_user
        
        # Get from database
        self.metrics_service.increment_counter('user_cache_miss')
        user = {'user_id': user_id, 'name': f'User {user_id}'}
        
        # Cache for next time
        self.cache_service.set(cache_key, user, ttl=3600)
        
        return user
    
    def save_user(self, user: Dict[str, Any]) -> bool:
        """Save user and invalidate cache."""
        user_id = user.get('user_id')
        if user_id:
            self.cache_service.set(f"user_{user_id}", None)  # Invalidate cache
        
        self.metrics_service.increment_counter('user_saved')
        return True


# =============================================================================
# 4. APPLICATION SERVICES WITH DI
# =============================================================================

@scoped
class NutritionService:
    """Main nutrition application service."""
    
    def __init__(
        self,
        nutrition_calculator: NutritionCalculatorService,
        meal_plan_generator: MealPlanGeneratorService,
        user_repository: UserRepositoryInterface,
        message_service: MessageService,
        cache_service: CacheService
    ):
        self.nutrition_calculator = nutrition_calculator
        self.meal_plan_generator = meal_plan_generator
        self.user_repository = user_repository
        self.message_service = message_service
        self.cache_service = cache_service
    
    def create_nutrition_plan(
        self,
        user_id: str,
        weight: float,
        height: float,
        age: int,
        gender: str,
        activity_level: str,
        dietary_restrictions: List[str] = None
    ) -> Dict[str, Any]:
        """Create complete nutrition plan for user."""
        # Get user data
        user = self.user_repository.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Calculate nutritional needs
        bmr = self.nutrition_calculator.calculate_bmr(weight, height, age, gender)
        daily_calories = self.nutrition_calculator.calculate_daily_calories(bmr, activity_level)
        
        # Create nutrition profile
        profile = NutritionProfile(
            user_id=user_id,
            daily_calories=daily_calories,
            protein_goal=daily_calories * 0.15 / 4,  # 15% of calories from protein
            carb_goal=daily_calories * 0.50 / 4,     # 50% of calories from carbs
            fat_goal=daily_calories * 0.35 / 9       # 35% of calories from fat
        )
        
        # Generate meal plan
        meal_plan = self.meal_plan_generator.generate_meal_plan(profile, dietary_restrictions)
        
        # Cache the plan
        self.cache_service.set(f"meal_plan_{user_id}", meal_plan, ttl=86400)  # 24 hours
        
        # Send confirmation message
        self.message_service.send_nutrition_reminder(
            user_id,
            f"Your new nutrition plan is ready! Daily goal: {daily_calories} calories."
        )
        
        return {
            'user_id': user_id,
            'profile': profile,
            'meal_plan': meal_plan,
            'bmr': bmr
        }


# =============================================================================
# 5. API HANDLERS WITH DI
# =============================================================================

@injectable()
class NutritionController:
    """REST API controller for nutrition endpoints."""
    
    def __init__(
        self,
        nutrition_service: NutritionService,
        metrics_service: MetricsService
    ):
        self.nutrition_service = nutrition_service
        self.metrics_service = metrics_service
    
    def create_plan_endpoint(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """POST /nutrition/plan endpoint."""
        try:
            plan = self.nutrition_service.create_nutrition_plan(
                user_id=request_data['user_id'],
                weight=request_data['weight'],
                height=request_data['height'],
                age=request_data['age'],
                gender=request_data['gender'],
                activity_level=request_data['activity_level'],
                dietary_restrictions=request_data.get('dietary_restrictions', [])
            )
            
            self.metrics_service.increment_counter('nutrition_plan_created')
            
            return {
                'status': 'success',
                'data': plan
            }
        
        except Exception as e:
            self.metrics_service.increment_counter('nutrition_plan_error')
            return {
                'status': 'error',
                'message': str(e)
            }


# =============================================================================
# 6. CONTAINER CONFIGURATION
# =============================================================================

def register_aws_services(container: Container) -> None:
    """Register AWS service clients."""
    # AWS Session
    container.register_factory(
        boto3.Session,
        lambda: boto3.Session(),
        lifetime=container.ServiceLifetime.SINGLETON
    )
    
    # DynamoDB Resource
    container.register_factory(
        'dynamodb_resource',
        lambda session: session.resource('dynamodb'),
        lifetime=container.ServiceLifetime.SINGLETON
    )
    
    # SNS Client
    container.register_factory(
        'sns_client',
        lambda session: session.client('sns'),
        lifetime=container.ServiceLifetime.SINGLETON
    )
    
    # Bedrock AI Client
    container.register_factory(
        'ai_client',
        lambda session: session.client('bedrock-runtime'),
        lifetime=container.ServiceLifetime.SINGLETON
    )


def register_configuration(container: Container) -> None:
    """Register configuration objects."""
    app_config = get_application_config()
    
    # Register individual config sections
    container.register_instance(DatabaseConfig, app_config.database)
    container.register_instance(AIConfig, app_config.ai)
    container.register_instance(MessagingConfig, app_config.messaging)
    
    # Register config dictionaries for services that need them
    container.register_instance('cache_config', {
        'redis_url': app_config.cache.redis_url,
        'default_ttl': app_config.cache.default_ttl
    })
    
    container.register_instance('monitoring_config', {
        'metrics_enabled': app_config.monitoring.metrics_enabled,
        'log_level': app_config.monitoring.log_level
    })


def register_domain_services(container: Container) -> None:
    """Register domain services."""
    container.register_scoped(NutritionCalculatorService)
    container.register_scoped(MealPlanGeneratorService)
    container.register_scoped(NutritionService)


def register_infrastructure_services(container: Container) -> None:
    """Register infrastructure services."""
    container.register_singleton(CacheService)
    container.register_singleton(MetricsService)
    container.register_scoped(MessageService)


def register_repositories(container: Container) -> None:
    """Register repository services."""
    # Register interface with implementation
    container.register_scoped(UserRepositoryInterface, DynamoDBUserRepository)


def register_api_services(container: Container) -> None:
    """Register API controllers."""
    container.register_scoped(NutritionController)


def create_production_container() -> Container:
    """Create fully configured container for production use."""
    container = Container()
    
    # Register services in dependency order
    register_configuration(container)
    register_aws_services(container)
    register_infrastructure_services(container)
    register_repositories(container)
    register_domain_services(container)
    register_api_services(container)
    
    # Validate all registrations
    issues = container.validate_services()
    if issues:
        print("Container validation issues:")
        for issue in issues:
            print(f"  - {issue}")
    
    return container


# =============================================================================
# 7. USAGE EXAMPLES
# =============================================================================

def example_usage():
    """Show how to use the DI container in practice."""
    
    # Create and configure container
    container = create_production_container()
    
    # Example 1: Resolve a simple service
    cache_service = container.resolve(CacheService)
    print(f"Cache service: {cache_service}")
    
    # Example 2: Resolve a complex service with dependencies
    nutrition_service = container.resolve(NutritionService)
    
    # Example 3: Use the service
    plan = nutrition_service.create_nutrition_plan(
        user_id="user123",
        weight=70.0,
        height=175.0,
        age=30,
        gender="male",
        activity_level="moderate",
        dietary_restrictions=["vegetarian"]
    )
    print(f"Created plan: {plan}")
    
    # Example 4: Use API controller
    controller = container.resolve(NutritionController)
    response = controller.create_plan_endpoint({
        'user_id': 'user456',
        'weight': 65.0,
        'height': 160.0,
        'age': 25,
        'gender': 'female',
        'activity_level': 'light'
    })
    print(f"API response: {response}")
    
    # Example 5: Use scoped services
    with container.create_scope():
        scoped_service = container.resolve(NutritionService)
        # All scoped services in this block share the same instances
        pass
    # Scoped instances are disposed when scope exits


if __name__ == "__main__":
    example_usage()
