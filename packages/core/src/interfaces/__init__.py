"""
Core interfaces package
Exports all interface definitions for domain-driven architecture
"""

from .repositories import (
    UserRepository,
    NutritionRepository,
    BusinessRepository,
    BrandRepository,
    CacheRepository
)

from .services import (
    NutritionAPIService,
    AIService,
    MessagingService,
    PaymentService,
    ConfigurationService,
    MonitoringService,
    NotificationService,
    FileStorageService,
    AnalyticsService
)

from .domain import (
    UserTier,
    DietaryRestriction,
    HealthGoal,
    NutritionProfile,
    UserProfile,
    Recipe,
    MealPlan,
    CostOptimizationResult,
    BrandMatch,
    RevenueEvent,
    DomainService,
    NutritionDomainService,
    BusinessDomainService
)

__all__ = [
    # Repository interfaces
    'UserRepository',
    'NutritionRepository', 
    'BusinessRepository',
    'BrandRepository',
    'CacheRepository',
    
    # Service interfaces
    'NutritionAPIService',
    'AIService',
    'MessagingService',
    'PaymentService',
    'ConfigurationService',
    'MonitoringService',
    'NotificationService',
    'FileStorageService',
    'AnalyticsService',
    
    # Domain models and services
    'UserTier',
    'DietaryRestriction',
    'HealthGoal',
    'NutritionProfile',
    'UserProfile',
    'Recipe',
    'MealPlan',
    'CostOptimizationResult',
    'BrandMatch',
    'RevenueEvent',
    'DomainService',
    'NutritionDomainService',
    'BusinessDomainService'
]

# Placeholder imports - these will be implemented as needed
__all__ = [
    # Placeholder for future interfaces
]
