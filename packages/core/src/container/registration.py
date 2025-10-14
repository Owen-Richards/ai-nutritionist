"""
Service Registration
===================

Centralized registration of all services in the monorepo.
"""

from typing import Type, Dict, Any
import os
from pathlib import Path

from .container import Container
from .lifetime import ServiceLifetime
from .providers import ConfigurationProvider, SecretProvider


class ServiceRegistration:
    """Handles registration of all application services."""
    
    @staticmethod
    def register_all_services(container: Container) -> Container:
        """Register all services in the application."""
        # Register infrastructure services first
        ServiceRegistration._register_infrastructure_services(container)
        
        # Register domain services
        ServiceRegistration._register_domain_services(container)
        
        # Register adapters and external services
        ServiceRegistration._register_adapters(container)
        
        # Register API and handler services
        ServiceRegistration._register_api_services(container)
        
        # Register configuration services
        ServiceRegistration._register_configuration_services(container)
        
        return container
    
    @staticmethod
    def _register_infrastructure_services(container: Container) -> None:
        """Register infrastructure services."""
        try:
            # AI Services
            from src.services.infrastructure.ai import AIService
            container.register_singleton(AIService)
            
            # Caching Services
            from src.services.infrastructure.caching import AdvancedCachingService
            container.register_singleton(AdvancedCachingService)
            
            # Resilience Services
            from src.services.infrastructure.resilience import ErrorRecoveryService
            container.register_singleton(ErrorRecoveryService)
            
            # Monitoring Services
            from src.services.infrastructure.monitoring import PerformanceMonitoringService
            container.register_singleton(PerformanceMonitoringService)
            
            # Experience Services
            from src.services.infrastructure.experience import EnhancedUserExperienceService
            container.register_singleton(EnhancedUserExperienceService)
            
            # Dashboard Services
            from src.services.infrastructure.dashboard import ImprovementDashboard
            container.register_singleton(ImprovementDashboard)
            
            # Observability Services
            from src.services.infrastructure.observability import ObservabilityService
            container.register_singleton(ObservabilityService)
            
            # Rate Limiting Services
            from src.services.infrastructure.distributed_rate_limiting import DistributedRateLimiter
            container.register_singleton(DistributedRateLimiter)
            
            # Secrets Management
            from src.services.infrastructure.secrets_manager import SecretsManager
            container.register_singleton(SecretsManager)
            
            # Privacy Compliance
            from src.services.infrastructure.privacy_compliance import PrivacyComplianceService
            container.register_singleton(PrivacyComplianceService)
            
            # Incident Management
            from src.services.infrastructure.incident_management import IncidentManager
            container.register_singleton(IncidentManager)
            
        except ImportError as e:
            print(f"Warning: Could not register infrastructure service: {e}")
    
    @staticmethod
    def _register_domain_services(container: Container) -> None:
        """Register domain services."""
        try:
            # Nutrition Services
            from src.services.nutrition.insights import NutritionInsightsService
            from src.services.nutrition.calculator import NutritionCalculator
            from src.services.nutrition.tracker import NutritionTracker
            container.register_scoped(NutritionInsightsService)
            container.register_scoped(NutritionCalculator)
            container.register_scoped(NutritionTracker)
            
            # Personalization Services
            from src.services.personalization.preferences import UserPreferenceService
            from src.services.personalization.learning import AdaptiveLearningService
            container.register_scoped(UserPreferenceService)
            container.register_scoped(AdaptiveLearningService)
            
            # Meal Planning Services
            from src.services.meal_planning.planner import MealPlannerService
            from src.services.meal_planning.optimizer import MealPlanService
            from src.services.meal_planning.plan_coordinator import PlanCoordinator
            from src.services.meal_planning.pipeline import MealPlanPipeline
            from src.services.meal_planning.rule_engine import RuleBasedMealPlanEngine
            container.register_scoped(MealPlannerService)
            container.register_scoped(MealPlanService)
            container.register_scoped(PlanCoordinator)
            container.register_scoped(MealPlanPipeline)
            container.register_scoped(RuleBasedMealPlanEngine)
            
            # Messaging Services
            from src.services.messaging.sms import ConsolidatedMessagingService
            from src.services.messaging.notifications import AWSMessagingService
            from src.services.messaging.templates import NutritionMessagingService
            from src.services.messaging.analytics import MultiUserMessagingHandler
            container.register_scoped(ConsolidatedMessagingService)
            container.register_scoped(AWSMessagingService)
            container.register_scoped(NutritionMessagingService)
            container.register_scoped(MultiUserMessagingHandler)
            
            # Business Services
            from src.services.business.subscription import SubscriptionService
            from src.services.business.revenue import RevenueOptimizationService
            container.register_scoped(SubscriptionService)
            container.register_scoped(RevenueOptimizationService)
            
            # Community Services
            from src.services.community.service import CommunityService
            from src.services.community.anonymization import AnonymizationService
            container.register_scoped(CommunityService)
            container.register_singleton(AnonymizationService)
            
            # Gamification Services
            from src.services.gamification.service import GamificationService
            container.register_scoped(GamificationService)
            
            # Analytics Services
            from src.services.analytics.analytics_service import AnalyticsService
            from src.services.analytics.warehouse_processor import WarehouseProcessor
            container.register_scoped(AnalyticsService)
            container.register_scoped(WarehouseProcessor)
            
            # Integration Services
            from src.services.integrations.calendar_service import CalendarService
            from src.services.integrations.fitness_service import FitnessService
            from src.services.integrations.grocery_service import GroceryService
            from src.services.integrations.health_sync_service import HealthSyncService
            container.register_scoped(CalendarService)
            container.register_scoped(FitnessService)
            container.register_scoped(GroceryService)
            container.register_scoped(HealthSyncService)
            
            # Engagement Services
            from src.services.engagement.cadence_engine import CadenceEngine
            container.register_scoped(CadenceEngine)
            
        except ImportError as e:
            print(f"Warning: Could not register domain service: {e}")
    
    @staticmethod
    def _register_adapters(container: Container) -> None:
        """Register adapter services."""
        try:
            # Database Adapters
            from src.adapters.dynamodb_repository import DynamoDBUserRepository
            container.register_scoped(DynamoDBUserRepository)
            
            # Messaging Adapters
            from src.adapters.messaging_adapters import AWSMessagingService as AdapterAWSMessagingService
            from src.adapters.messaging_adapters import WhatsAppMessagingService
            container.register_scoped(AdapterAWSMessagingService)
            container.register_scoped(WhatsAppMessagingService)
            
            # AI Adapters
            from src.adapters.bedrock_ai import BedrockAIService
            container.register_singleton(BedrockAIService)
            
            # AWS Service Clients
            import boto3
            container.register_factory(
                boto3.Session,
                lambda: boto3.Session(),
                ServiceLifetime.SINGLETON
            )
            
            # DynamoDB Resource
            container.register_factory(
                'dynamodb_resource',
                lambda session=boto3.Session: session.resource('dynamodb'),
                ServiceLifetime.SINGLETON
            )
            
        except ImportError as e:
            print(f"Warning: Could not register adapter: {e}")
    
    @staticmethod
    def _register_api_services(container: Container) -> None:
        """Register API and handler services."""
        try:
            # Repository Services
            from src.services.meal_planning.repository import InMemoryPlanRepository
            from src.services.meal_planning.data_store import InMemoryPlanDataStore
            from src.services.community.repository import CommunityRepository
            container.register_singleton(InMemoryPlanRepository)
            container.register_singleton(InMemoryPlanDataStore)
            container.register_singleton(CommunityRepository)
            
            # Logging Services
            from src.services.meal_planning.ml_logging import FeatureLogger
            container.register_singleton(FeatureLogger)
            
        except ImportError as e:
            print(f"Warning: Could not register API service: {e}")
    
    @staticmethod
    def _register_configuration_services(container: Container) -> None:
        """Register configuration and secret services."""
        # Configuration classes
        container.register_factory(
            'database_config',
            lambda: {
                'table_name': os.getenv('DYNAMODB_TABLE_NAME', 'ai-nutritionist-users'),
                'region': os.getenv('AWS_REGION', 'us-east-1')
            },
            ServiceLifetime.SINGLETON
        )
        
        container.register_factory(
            'api_config',
            lambda: {
                'cors_origins': os.getenv('CORS_ORIGINS', '*').split(','),
                'debug': os.getenv('DEBUG', 'false').lower() == 'true',
                'rate_limit': int(os.getenv('RATE_LIMIT', '100'))
            },
            ServiceLifetime.SINGLETON
        )
        
        container.register_factory(
            'ai_config',
            lambda: {
                'model_name': os.getenv('AI_MODEL_NAME', 'anthropic.claude-3-sonnet-20240229-v1:0'),
                'region': os.getenv('AWS_REGION', 'us-east-1'),
                'max_tokens': int(os.getenv('AI_MAX_TOKENS', '4000'))
            },
            ServiceLifetime.SINGLETON
        )


class ServiceModule:
    """Base class for service modules that can register services."""
    
    def register_services(self, container: Container) -> None:
        """Register services in this module."""
        raise NotImplementedError
    
    def get_dependencies(self) -> list:
        """Get list of dependency modules."""
        return []


class NutritionModule(ServiceModule):
    """Nutrition domain service module."""
    
    def register_services(self, container: Container) -> None:
        """Register nutrition services."""
        try:
            from src.services.nutrition.insights import NutritionInsightsService
            from src.services.nutrition.calculator import NutritionCalculator
            from src.services.nutrition.tracker import NutritionTracker
            
            container.register_scoped(NutritionInsightsService)
            container.register_scoped(NutritionCalculator)
            container.register_scoped(NutritionTracker)
        except ImportError:
            pass


class PersonalizationModule(ServiceModule):
    """Personalization domain service module."""
    
    def register_services(self, container: Container) -> None:
        """Register personalization services."""
        try:
            from src.services.personalization.preferences import UserPreferenceService
            from src.services.personalization.learning import AdaptiveLearningService
            
            container.register_scoped(UserPreferenceService)
            container.register_scoped(AdaptiveLearningService)
        except ImportError:
            pass


class MealPlanningModule(ServiceModule):
    """Meal planning domain service module."""
    
    def register_services(self, container: Container) -> None:
        """Register meal planning services."""
        try:
            from src.services.meal_planning.planner import MealPlannerService
            from src.services.meal_planning.optimizer import MealPlanService
            from src.services.meal_planning.plan_coordinator import PlanCoordinator
            
            container.register_scoped(MealPlannerService)
            container.register_scoped(MealPlanService)
            container.register_scoped(PlanCoordinator)
        except ImportError:
            pass


class MessagingModule(ServiceModule):
    """Messaging domain service module."""
    
    def register_services(self, container: Container) -> None:
        """Register messaging services."""
        try:
            from src.services.messaging.sms import ConsolidatedMessagingService
            from src.services.messaging.notifications import AWSMessagingService
            
            container.register_scoped(ConsolidatedMessagingService)
            container.register_scoped(AWSMessagingService)
        except ImportError:
            pass


class InfrastructureModule(ServiceModule):
    """Infrastructure service module."""
    
    def register_services(self, container: Container) -> None:
        """Register infrastructure services."""
        try:
            from src.services.infrastructure.ai import AIService
            from src.services.infrastructure.caching import AdvancedCachingService
            from src.services.infrastructure.monitoring import PerformanceMonitoringService
            
            container.register_singleton(AIService)
            container.register_singleton(AdvancedCachingService)
            container.register_singleton(PerformanceMonitoringService)
        except ImportError:
            pass


def create_configured_container() -> Container:
    """Create and configure a fully registered container."""
    container = Container()
    
    # Register all services
    ServiceRegistration.register_all_services(container)
    
    # Validate services
    issues = container.validate_services()
    if issues:
        print("Service registration issues found:")
        for issue in issues:
            print(f"  - {issue}")
    
    return container
