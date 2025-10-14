"""
Domain services package
Contains pure business logic separated from infrastructure
"""

from .nutrition_calculation import NutritionCalculationService
from .user_management import UserManagementService
from .business_logic import BusinessLogicService

# Legacy imports for backward compatibility  
try:
    from .meal_planning import MealPlanningDomainService
    from .user_matching import UserMatchingService
    from .pricing import PricingService
except ImportError:
    pass

__all__ = [
    'NutritionCalculationService',
    'UserManagementService', 
    'BusinessLogicService',
    # Legacy exports
    'MealPlanningDomainService',
    'UserMatchingService',
    'PricingService'
]