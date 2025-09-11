"""
AI Nutritionist Service Layer
============================

Enterprise-grade domain-driven architecture with 6 organized service domains:

DOMAIN STRUCTURE:
├── nutrition/           - Nutrition analysis, tracking, and insights
├── personalization/     - User profiling and adaptive learning  
├── meal_planning/       - Advanced meal planning with multi-goal support
├── messaging/           - Multi-platform communication services
├── business/            - Revenue generation and business operations
└── infrastructure/      - Technical foundation and system services

CLEAN ARCHITECTURE BENEFITS:
✅ No scattered service files
✅ Clear domain boundaries
✅ Logical service organization
✅ Easy maintenance and scaling
✅ Enterprise-grade structure
✅ Domain-driven design principles

IMPORT EXAMPLES:
from services.nutrition import NutritionTracker, NutritionCalculator
from services.personalization import UserPreferencesService
from services.meal_planning import MealPlanningService
from services.messaging import SMSCommunicationService
from services.business import SubscriptionService
from services.infrastructure import AIService

This structure eliminates the previous chaos of 30+ scattered service files
and provides a world-class, maintainable service architecture.
"""

# Core domain exports (lazy loading to avoid circular imports)
__all__ = [
    # Service domains
    'nutrition',
    'personalization', 
    'meal_planning',
    'messaging',
    'business',
    'infrastructure'
]

# Core domain exports (lazy loading to avoid circular imports)
__all__ = [
    # Service domains
    'nutrition',
    'personalization', 
    'meal_planning',
    'messaging',
    'business',
    'infrastructure'
]

# Domain access functions to avoid circular imports
def get_nutrition_services():
    """Get nutrition domain services"""
    from .nutrition import NutritionTracker, NutritionCalculator, NutritionInsights
    return {
        'tracker': NutritionTracker,
        'calculator': NutritionCalculator,
        'insights': NutritionInsights
    }

def get_personalization_services():
    """Get personalization domain services"""
    from .personalization import UserPreferencesService, UserLearningService, UserBehaviorService
    return {
        'preferences': UserPreferencesService,
        'learning': UserLearningService,
        'behavior': UserBehaviorService
    }

def get_meal_planning_services():
    """Get meal planning domain services"""
    from .meal_planning import MealPlanningService, MealOptimizer
    return {
        'planner': MealPlanningService,
        'optimizer': MealOptimizer
    }

def get_messaging_services():
    """Get messaging domain services"""
    from .messaging import SMSCommunicationService, NotificationService
    return {
        'sms': SMSCommunicationService,
        'notifications': NotificationService
    }

def get_business_services():
    """Get business domain services"""
    from .business import SubscriptionService, RevenueOptimizationService
    return {
        'subscription': SubscriptionService,
        'revenue': RevenueOptimizationService
    }

def get_infrastructure_services():
    """Get infrastructure domain services"""
    from .infrastructure import AIService, AdvancedCachingService
    return {
        'ai': AIService,
        'caching': AdvancedCachingService
    }
