"""
AI Nutritionist Service Contract Schemas

Defines schemas for all service contracts in the AI Nutritionist application.
"""

from .nutrition_schemas import NutritionServiceSchemas
from .meal_planning_schemas import MealPlanningServiceSchemas
from .messaging_schemas import MessagingServiceSchemas
from .business_schemas import BusinessServiceSchemas
from .infrastructure_schemas import InfrastructureServiceSchemas
from .analytics_schemas import AnalyticsServiceSchemas

__all__ = [
    "NutritionServiceSchemas",
    "MealPlanningServiceSchemas", 
    "MessagingServiceSchemas",
    "BusinessServiceSchemas",
    "InfrastructureServiceSchemas",
    "AnalyticsServiceSchemas"
]
