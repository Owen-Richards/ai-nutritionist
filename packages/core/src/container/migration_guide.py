"""
Service Migration Guide
======================

Step-by-step guide for migrating existing services to use dependency injection.
"""

from typing import Dict, Any, Optional, List
import boto3
from dataclasses import dataclass

from packages.core.src.container import Container, injectable, singleton, scoped


# =============================================================================
# BEFORE: Services without DI (Anti-patterns)
# =============================================================================

class LegacyNutritionService:
    """
    Legacy service with tightly coupled dependencies.
    This is what we want to AVOID.
    """
    
    def __init__(self):
        # ❌ ANTI-PATTERN: Creating dependencies directly
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table('ai-nutritionist-users')
        self.ai_client = boto3.client('bedrock-runtime')
        
        # ❌ ANTI-PATTERN: Hard-coded configuration
        self.model_name = 'anthropic.claude-3-sonnet-20240229-v1:0'
        self.region = 'us-east-1'
        
        # ❌ ANTI-PATTERN: Creating other services directly
        self.cache_service = self._create_cache_service()
    
    def _create_cache_service(self):
        """❌ ANTI-PATTERN: Manual service creation"""
        import redis
        return redis.Redis(host='localhost', port=6379, db=0)
    
    def get_nutrition_advice(self, user_id: str, food_item: str) -> str:
        """Get nutrition advice for a food item."""
        # Business logic mixed with infrastructure concerns
        user_data = self.table.get_item(Key={'user_id': user_id})
        
        # Direct AI client usage
        response = self.ai_client.invoke_model(
            modelId=self.model_name,
            body=f'{{"prompt": "Nutrition advice for {food_item}"}}'
        )
        
        return "Nutrition advice"


class LegacyUserService:
    """Legacy user service with service locator anti-pattern."""
    
    def __init__(self):
        # ❌ ANTI-PATTERN: Service locator
        self.service_locator = GlobalServiceLocator.instance()
        
    def create_user(self, user_data: Dict[str, Any]) -> bool:
        """Create a new user."""
        # ❌ ANTI-PATTERN: Using service locator
        db_service = self.service_locator.get_service('database')
        email_service = self.service_locator.get_service('email')
        
        # Business logic
        db_service.save_user(user_data)
        email_service.send_welcome_email(user_data['email'])
        
        return True


class GlobalServiceLocator:
    """❌ ANTI-PATTERN: Global service locator"""
    
    _instance = None
    
    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self.services = {}
    
    def register_service(self, name: str, service: Any):
        self.services[name] = service
    
    def get_service(self, name: str):
        return self.services.get(name)


# =============================================================================
# AFTER: Services with DI (Best practices)
# =============================================================================

@dataclass
class NutritionConfig:
    """Configuration for nutrition services."""
    model_name: str
    region: str
    max_tokens: int = 4000
    temperature: float = 0.7


@injectable()
class NutritionService:
    """
    ✅ Properly designed service with dependency injection.
    """
    
    def __init__(
        self,
        user_repository: 'UserRepository',
        ai_service: 'AIService',
        cache_service: 'CacheService',
        nutrition_config: NutritionConfig
    ):
        # ✅ Dependencies injected via constructor
        self.user_repository = user_repository
        self.ai_service = ai_service
        self.cache_service = cache_service
        self.config = nutrition_config
    
    def get_nutrition_advice(self, user_id: str, food_item: str) -> str:
        """Get nutrition advice for a food item."""
        # ✅ Clean business logic using injected dependencies
        user = self.user_repository.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Check cache first
        cache_key = f"nutrition_{user_id}_{food_item}"
        cached_advice = self.cache_service.get(cache_key)
        if cached_advice:
            return cached_advice
        
        # Generate new advice
        prompt = f"Provide nutrition advice for {food_item} for user with preferences: {user.get('dietary_preferences', [])}"
        advice = self.ai_service.generate_response(prompt)
        
        # Cache the result
        self.cache_service.set(cache_key, advice, ttl=3600)
        
        return advice


@injectable()
class UserService:
    """✅ User service with proper dependency injection."""
    
    def __init__(
        self,
        user_repository: 'UserRepository',
        email_service: 'EmailService',
        notification_service: 'NotificationService'
    ):
        # ✅ Clear dependency declaration
        self.user_repository = user_repository
        self.email_service = email_service
        self.notification_service = notification_service
    
    def create_user(self, user_data: Dict[str, Any]) -> bool:
        """Create a new user."""
        # ✅ Clean business logic
        user_id = self.user_repository.save_user(user_data)
        
        # Send welcome email
        self.email_service.send_welcome_email(user_data['email'])
        
        # Send notification to admin
        self.notification_service.notify_new_user(user_id)
        
        return True


# =============================================================================
# MIGRATION STEPS
# =============================================================================

class ServiceMigrationGuide:
    """Guide for migrating legacy services to DI."""
    
    @staticmethod
    def step_1_identify_dependencies():
        """
        Step 1: Identify all dependencies in legacy service.
        
        Look for:
        - Direct instantiation of other classes
        - boto3.client() or boto3.resource() calls
        - Hard-coded configuration values
        - Global variable access
        - Service locator pattern usage
        """
        print("""
        🔍 STEP 1: Identify Dependencies
        
        In your legacy service, look for:
        ❌ self.dynamodb = boto3.resource('dynamodb')
        ❌ self.config = {'api_key': 'hardcoded_value'}
        ❌ self.other_service = OtherService()
        ❌ from app import global_cache
        ❌ service = ServiceLocator.get('service_name')
        """)
    
    @staticmethod
    def step_2_extract_dependencies():
        """
        Step 2: Extract dependencies to constructor parameters.
        """
        print("""
        🔧 STEP 2: Extract Dependencies
        
        Transform:
        ❌ class MyService:
               def __init__(self):
                   self.db = boto3.resource('dynamodb')
        
        To:
        ✅ @injectable()
           class MyService:
               def __init__(self, dynamodb_resource):
                   self.db = dynamodb_resource
        """)
    
    @staticmethod
    def step_3_add_di_decorators():
        """
        Step 3: Add dependency injection decorators.
        """
        print("""
        🏷️ STEP 3: Add DI Decorators
        
        Choose appropriate decorator:
        - @singleton    - One instance for entire application
        - @scoped       - One instance per request/scope
        - @transient    - New instance every time
        - @injectable() - Default (transient)
        
        Examples:
        @singleton      # For caches, configurations, clients
        class CacheService: ...
        
        @scoped         # For business services, handlers
        class UserService: ...
        
        @transient      # For repositories, adapters
        class UserRepository: ...
        """)
    
    @staticmethod
    def step_4_register_services():
        """
        Step 4: Register services in container.
        """
        print("""
        📋 STEP 4: Register Services
        
        In your container configuration:
        
        container.register_singleton(CacheService)
        container.register_scoped(UserService)
        container.register_transient(UserRepository)
        
        Or use auto-registration:
        from packages.core.src.container.auto_registration import create_auto_configured_container
        container = create_auto_configured_container()
        """)
    
    @staticmethod
    def step_5_test_migration():
        """
        Step 5: Test the migrated service.
        """
        print("""
        🧪 STEP 5: Test Migration
        
        # Create test container
        container = Container()
        container.register_all_services()
        
        # Test service resolution
        service = container.resolve(MyService)
        result = service.my_method()
        
        # Verify dependencies are injected correctly
        assert service.dependency is not None
        """)


# =============================================================================
# MIGRATION EXAMPLE: COMPLETE TRANSFORMATION
# =============================================================================

def migration_example():
    """Complete example of migrating a legacy service."""
    
    print("🔄 MIGRATION EXAMPLE")
    print("=" * 50)
    
    # ❌ BEFORE: Legacy service
    print("\n❌ BEFORE (Legacy service):")
    print("""
    class LegacyMealPlanService:
        def __init__(self):
            self.dynamodb = boto3.resource('dynamodb')
            self.ai_client = boto3.client('bedrock-runtime')
            self.cache = redis.Redis()
            self.model_name = 'claude-3-sonnet'
        
        def generate_plan(self, user_id: str):
            user = self.dynamodb.Table('users').get_item(Key={'id': user_id})
            ai_response = self.ai_client.invoke_model(...)
            self.cache.set(f'plan_{user_id}', ai_response)
            return ai_response
    """)
    
    # ✅ AFTER: DI-enabled service
    print("\n✅ AFTER (DI-enabled service):")
    print("""
    @injectable()
    class MealPlanService:
        def __init__(
            self,
            user_repository: UserRepository,
            ai_service: AIService,
            cache_service: CacheService,
            ai_config: AIConfig
        ):
            self.user_repository = user_repository
            self.ai_service = ai_service
            self.cache_service = cache_service
            self.ai_config = ai_config
        
        def generate_plan(self, user_id: str):
            user = self.user_repository.get_user(user_id)
            ai_response = self.ai_service.generate_meal_plan(user, self.ai_config)
            self.cache_service.set(f'plan_{user_id}', ai_response)
            return ai_response
    """)
    
    print("\n📊 Benefits of migration:")
    print("✅ Testable - Dependencies can be mocked")
    print("✅ Configurable - No hard-coded values")
    print("✅ Maintainable - Clear dependency relationships")
    print("✅ Scalable - Easy to swap implementations")
    print("✅ SOLID principles - Single responsibility, dependency inversion")


# =============================================================================
# PRACTICAL MIGRATION TOOLS
# =============================================================================

class MigrationAnalyzer:
    """Analyzes existing code for migration opportunities."""
    
    def __init__(self, source_path: str):
        self.source_path = source_path
        self.issues = []
        self.suggestions = []
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a Python file for DI migration opportunities."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            issues = []
            suggestions = []
            
            # Check for anti-patterns
            if 'boto3.client(' in content or 'boto3.resource(' in content:
                issues.append("Direct AWS service instantiation found")
                suggestions.append("Inject AWS clients via constructor")
            
            if 'redis.Redis(' in content:
                issues.append("Direct Redis instantiation found")
                suggestions.append("Inject CacheService via constructor")
            
            if 'global ' in content:
                issues.append("Global variables found")
                suggestions.append("Use dependency injection instead of globals")
            
            if 'ServiceLocator' in content:
                issues.append("Service locator pattern found")
                suggestions.append("Replace with constructor injection")
            
            # Check for hardcoded configuration
            hardcoded_patterns = ['us-east-1', 'localhost:', 'api_key =', 'secret =']
            for pattern in hardcoded_patterns:
                if pattern in content:
                    issues.append(f"Hardcoded configuration found: {pattern}")
                    suggestions.append("Move configuration to config classes")
            
            return {
                'file': file_path,
                'issues': issues,
                'suggestions': suggestions,
                'migration_priority': len(issues)
            }
        
        except Exception as e:
            return {
                'file': file_path,
                'error': str(e),
                'migration_priority': 0
            }
    
    def generate_migration_plan(self, analysis_results: List[Dict[str, Any]]) -> str:
        """Generate a migration plan based on analysis."""
        plan = []
        
        # Sort by priority (most issues first)
        sorted_results = sorted(
            analysis_results, 
            key=lambda x: x.get('migration_priority', 0), 
            reverse=True
        )
        
        plan.append("🗺️ MIGRATION PLAN")
        plan.append("=" * 40)
        
        for i, result in enumerate(sorted_results[:10], 1):  # Top 10
            if result.get('migration_priority', 0) > 0:
                plan.append(f"\n{i}. {result['file']}")
                plan.append(f"   Priority: {result['migration_priority']} issues")
                
                for issue in result.get('issues', []):
                    plan.append(f"   ❌ {issue}")
                
                for suggestion in result.get('suggestions', []):
                    plan.append(f"   ✅ {suggestion}")
        
        return '\n'.join(plan)


def create_migration_checklist():
    """Create a migration checklist for teams."""
    
    checklist = """
    📋 DI MIGRATION CHECKLIST
    ========================
    
    □ Step 1: Dependency Analysis
      □ Identify all external dependencies
      □ List hardcoded configuration values
      □ Find service locator usage
      □ Document current service relationships
    
    □ Step 2: Design Phase
      □ Define service interfaces
      □ Choose appropriate lifetimes
      □ Plan configuration structure
      □ Design service boundaries
    
    □ Step 3: Implementation
      □ Add @injectable decorators
      □ Convert constructor parameters
      □ Extract configuration classes
      □ Create service factories if needed
    
    □ Step 4: Registration
      □ Register services in container
      □ Configure lifetimes correctly
      □ Set up auto-registration if desired
      □ Register configuration providers
    
    □ Step 5: Testing
      □ Write unit tests with mocked dependencies
      □ Test service resolution
      □ Validate configuration injection
      □ Test different lifetime scopes
    
    □ Step 6: Integration
      □ Update application startup code
      □ Migrate existing service calls
      □ Remove old service locators
      □ Clean up hardcoded dependencies
    
    □ Step 7: Validation
      □ Run full test suite
      □ Check container validation
      □ Monitor for circular dependencies
      □ Verify performance impact
    
    ✅ Migration Complete!
    """
    
    return checklist


if __name__ == "__main__":
    print("🚀 Service Migration Guide")
    print("=" * 50)
    
    # Show migration steps
    guide = ServiceMigrationGuide()
    guide.step_1_identify_dependencies()
    guide.step_2_extract_dependencies()
    guide.step_3_add_di_decorators()
    guide.step_4_register_services()
    guide.step_5_test_migration()
    
    # Show complete example
    migration_example()
    
    # Show checklist
    print(create_migration_checklist())
